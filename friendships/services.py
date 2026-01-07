import time

from django.conf import settings
from django.core.cache import caches

from friendships.models import Friendship, HBaseFollowing, HBaseFollower
from gatekeeper.models import Gatekeeper
from twitter.cache import FOLLOWINGS_PATTERN

cache = caches['testing'] if settings.TESTING else caches['default']


class FriendshipService(object):

    @classmethod
    def get_followers(cls, user):
        # ⚠️ legacy function
        # 错误的写法一：会导致 N + 1 Queries 的问题;
        # 1 Query: filter 出所有 friendships
        # N Query: for 循环每个 friendship 取 from_user
        # friendships = Friendship.objects.filter(to_user=user)
        # return [friendship.from_user for friendship in friendships]

        # 错误的写法二
        # 这种写法是使用了 JOIN 操作，让 friendship table 和 user table 在 from_user
        # 这个属性上 join 了起来。join 操作在大规模用户的 web 场景下是禁用的，因为非常慢。
        # friendships = Friendship.objects.filter(
        #     to_user=user
        # ).select_related('from_user')
        # return [friendship.from_user for friendship in friendships]

        # SELECT * FROM `friendships_friendship`
        # INNER JOIN `auth_user`
        # ON "friendships_friendship"."from_user_id" = "auth_user"."id"
        # WHERE friendships_friendship"."to_user_id" = <user.id>;
        # ========================================================================

        # 正确的写法一，自己手动 filter id，使用 IN Query 查询
        # friendships = Friendship.objects.filter(to_user=user)
        # follower_ids = [friendship.from_user_id for friendship in friendships]
        # followers = User.objects.filter(id__in=follower_ids)

        # 正确的写法二，使用 prefetch_related，会自动执行成两条语句，用 In Query 查询
        # 实际执行的 SQL 查询和上面是一样的，一共两条 SQL Queries
        # 1. SELECT * FROM `friendships_friendship`
        #    WHERE `friendships_friendship`.`to_user_id` = <user.id>;
        # 2. SELECT * FROM `auth_user` WHERE `auth_user`.`id` IN <follower_ids>;
        friendships = Friendship.objects.filter(
            to_user=user,
        ).prefetch_related('from_user')
        # prefetch_related('from_user') 并不会立即查询数据库，而是
        # 1. 在 QuerySet 上标记：告诉 Django “当你真正访问 from_user 时，请批量取出相关对象”
        # 2. 延迟执行：数据库查询会在你访问数据时触发（比如迭代或 list(friendships)）
        # 3. 执行后: QuerySet 中每个 friendship.from_user 会被 指向缓存好的 User 实例，不会再发 SQL
        #    {from_user_id1: <User instance>,
        #     from_user_id2: <User instance>, ...}
        return [friendship.from_user for friendship in friendships]

    @classmethod
    def get_follower_user_id_list(cls, to_user_id):
        # 正确的写法三: 直接用 user_id instead of user
        # .values: select * ==> select from_user_id
        # friendships = Friendship.objects.filter(to_user_id=to_user_id).values('from_user_id')
        # return [friendship['from_user_id'] for friendship in friendships]

        # Friendship.objects.values_list('from_user_id')            [(1,), (5,), (9,)]
        # Friendship.objects.values_list('from_user_id', flat=True) [1, 5, 9]
        # flat=True: 只能在“只选一个字段”时使用, 把 (value,) 压扁成 value
        # from_user_ids = Friendship.objects.filter(to_user_id=to_user_id).values_list('from_user_id', flat=True)
        if not Gatekeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
            friendships = Friendship.objects.filter(to_user_id=to_user_id)
        else:
           friendships = HBaseFollower.filter(prefix=(to_user_id, None))
        return [friendship.from_user_id for friendship in friendships]

    @classmethod
    def get_following_user_id_set(cls, from_user_id):   # memcached 缓存
        # TODO [Homework] cache in redis set
        key = FOLLOWINGS_PATTERN.format(user_id=from_user_id)
        user_id_set = cache.get(key)
        if user_id_set is not None: # key 如果不存在, 也不会报错 return None
            return user_id_set

        if not Gatekeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
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
        # if not Gatekeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
        #     return Friendship.objects.filter(
        #         from_user_id=from_user_id,
        #         to_user_id=to_user_id,
        #     ).exists()
        #
        # instance = cls.get_follow_instance(from_user_id=from_user_id, to_user_id=to_user_id)
        # return instance is not None

    @classmethod
    def follow(cls, from_user_id, to_user_id):
        if from_user_id == to_user_id:
            return None

        if not Gatekeeper.is_switch_on('switch_friendship_to_hbase'):
            # 1. create data in MySQL
            friendship = Friendship.objects.create(
                # Friendship.objects.create(from_user=user_obj)
                # Friendship.objects.create(from_user_id=1)
                from_user_id=from_user_id,
                to_user_id=to_user_id,
            )
            return friendship

        # 2. create data in hbase
        # 关注关系需要同时写入 HBaseFollower 和  HBaseFollowing 两张表
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

        if not Gatekeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
            # https://docs.djangoproject.com/en/3.1/ref/models/querysets/#delete
            # Queryset 的 delete 操作返回两个值，一个是删了多少数据，一个是具体每种类型删了多少
            # 为什么会出现多种类型数据的删除？因为可能因为 foreign key 设置了 cascade 出现级联
            # 删除，也就是比如 A model(学生) 的某个属性是 B model(班级) 的 foreign key，并且设置了
            # on_delete=models.CASCADE, 那么当 B 的某个数据被删除的时候，A 中的关联也会被删除。
            # 所以 CASCADE 是很危险的，我们一般最好不要用，而是用 on_delete=models.SET_NULL
            # 取而代之，这样至少可以避免误删除操作带来的多米诺效应。
            deleted, _ = Friendship.objects.filter(
                from_user_id=from_user_id,
                to_user_id=to_user_id,
            ).delete()  # 没有 follow 的情况下 unfollow 静默处理
            return deleted

        instance = cls.get_follow_instance(from_user_id=from_user_id, to_user_id=to_user_id)
        if instance is None:
            return 0

        HBaseFollowing.delete(from_user_id=from_user_id, created_at=instance.created_at)
        HBaseFollower.delete(to_user_id=to_user_id, created_at=instance.created_at)
        return 1

    @classmethod
    def get_following_count(cls, from_user_id):
        user_id_set = cls.get_following_user_id_set(from_user_id=from_user_id)
        return len(user_id_set)

        # ⚠️ legacy code
        # if not Gatekeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
        #     return Friendship.objects.filter(from_user_id=from_user_id).count()
        #
        # followings = HBaseFollowing.filter(prefix=(from_user_id, None))
        # return len(followings)