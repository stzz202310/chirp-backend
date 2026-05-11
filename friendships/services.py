import time

from django.conf import settings
from django.core.cache import caches

from friendships.models import Friendship, HBaseFollowing, HBaseFollower
from gatekeeper.models import GateKeeper
from twitter.cache import FOLLOWINGS_PATTERN

cache = caches['testing'] if settings.TESTING else caches['default']


class FriendshipService(object):

    @classmethod
    def get_followers(cls, user):
        # ⚠️ legacy function
        friendships = Friendship.objects.filter(to_user=user).prefetch_related('from_user')
        return [friendship.from_user for friendship in friendships]

    @classmethod
    def get_follower_user_id_list(cls, to_user_id):
        if not GateKeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
            # friendships = Friendship.objects.filter(to_user_id=to_user_id).values('from_user_id')
            # return [friendship['from_user_id'] for friendship in friendships]
            # .filter(...).values(...): select * => select `from_user_id` from `friendships_friendship`
            friendships = Friendship.objects.filter(to_user_id=to_user_id)
        else:
           friendships = HBaseFollower.filter(prefix=(to_user_id, None))
        return [friendship.from_user_id for friendship in friendships]

    @classmethod
    def get_following_user_id_set(cls, from_user_id):   # memcached 缓存
        # TODO [Homework] cache in redis set
        key = FOLLOWINGS_PATTERN.format(user_id=from_user_id)
        user_id_set = cache.get(key)    # key 不存在 → 返回 None
        if user_id_set is not None:
            return user_id_set

        if not GateKeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
            friendships = Friendship.objects.filter(from_user_id=from_user_id)
        else:
            friendships = HBaseFollowing.filter(prefix=(from_user_id,))

        user_id_set = set([friendship.to_user_id for friendship in friendships])
        cache.set(key, user_id_set)
        return user_id_set

    @classmethod
    def invalidate_following_cache(cls, from_user_id):
        key = FOLLOWINGS_PATTERN.format(user_id=from_user_id)
        cache.delete(key)

    @classmethod
    def get_follow_instance(cls, from_user_id, to_user_id):
        # HBase Only: 通过 from_user_id 和 to_user_id 找到对应的 instance
        # 时间复杂度 O(n), n = 该用户的关注数量 (关注越多，查询越慢)
        followings = HBaseFollowing.filter(prefix=(from_user_id,))
        for follow in followings:
            if follow.to_user_id == to_user_id:
                return follow
        return None

    @classmethod
    def has_followed(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return False
        return to_user_id in cls.get_following_user_id_set(from_user_id=from_user_id)
        # ⚠️ legacy code
        # if not GateKeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
        #     return Friendship.objects.filter(
        #         from_user_id=from_user_id,
        #         to_user_id=to_user_id,
        #     ).exists()
        #
        # instance = cls.get_follow_instance(from_user_id=from_user_id, to_user_id=to_user_id)
        # return instance is not None

    @classmethod
    def get_following_count(cls, from_user_id):
        user_id_set = cls.get_following_user_id_set(from_user_id=from_user_id)
        return len(user_id_set)
        # ⚠️ legacy code
        # if not GateKeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
        #     return Friendship.objects.filter(from_user_id=from_user_id).count()
        #
        # followings = HBaseFollowing.filter(prefix=(from_user_id, None))
        # return len(followings)

    @classmethod
    def follow(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return None

        if not GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            # 1. create data in MySQL
            friendship = Friendship.objects.create(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
            )
            return friendship

        # 2. create data in hbase (HBaseFollower + HBaseFollowing)
        # 两张表结构一致[仅 RowKey 设计不同, 用于支持高效的双向查询], 返回任意一个即可
        now = int(time.time() * 1000000)
        HBaseFollower.create(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            created_at=now,
        )
        return HBaseFollowing.create(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
            created_at=now,
        )

    @classmethod
    def unfollow(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return 0

        if not GateKeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
            # Django ORM: QuerySet.delete() 返回 tuple(deleted, detail)
            # deleted: int  本次操作删除的对象总数 (含级联删除 CASCADE)
            # detail:  dict 各模型被删除的数量 {'app_label.ModelName': count, ...}
            deleted, _ = Friendship.objects.filter(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
            ).delete()  # 没有关注(follow)的情况下取关(unfollow): 静默处理
            return deleted

        instance = cls.get_follow_instance(from_user_id=from_user_id, to_user_id=to_user_id)
        if instance is None:
            return 0

        HBaseFollowing.delete(from_user_id=from_user_id, created_at=instance.created_at)
        HBaseFollower.delete(to_user_id=to_user_id, created_at=instance.created_at)
        return 1