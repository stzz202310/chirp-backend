from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, pre_delete

from friendships.listeners import invalidate_following_cache
from utils.memcached_helper import MemcachedHelper


class Friendship(models.Model):
    # user.friendship_set.all() 等价于 Friendship.objects.filter(from_user|to_user无法区分 = user)
    # 所以需要定义 related_name [user.tweet_set.all() 不需要定义 related_name]
    # user.following_friendship_set.all(): user 作为 from_user set{我关注的所有人} 关注列表
    # user.follower_friendship_set.all():  user 作为 to_user   set{关注我的所有人} 粉丝列表
    # 等价于
    # Friendship.objects.filter(from_user=user)
    # Friendship.objects.filter(to_user=user)
    from_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='following_friendship_set',
    )

    to_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='follower_friendship_set',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            ('from_user', 'created_at'), # 关注列表 from_user=我: 获取我关注的所有人，按照关注时间排序
            ('to_user', 'created_at'),   # 粉丝列表 to_user=我:   获取关注我的所有人，按照关注时间排序
        )
        # instance.save() → SQL INSERT/UPDATE 时检查 Django model {models.py}
        # 1. content = models.TextField(max_length=140)
        # 2. unique_together [数据库层面 防止 重复关注]
        # 5XX 错误: (1062, "Duplicate entry '1-2' for key
        #   'friendships_friendship.friendships_friendship_from_user_id_to_user_id_c3116feb_uniq'")
        unique_together = (('from_user', 'to_user'),)
        ordering = ('-created_at',) # 对所有的查询结果 QuerySet 都有效

    def __str__(self):
        return '{} followed {}'.format(self.from_user_id, self.to_user_id)

    @property
    def cached_from_user(self):
        return MemcachedHelper.get_object_through_cache(
            model_class=User,
            object_id=self.from_user_id
        )

    @property
    def cached_to_user(self):
        return MemcachedHelper.get_object_through_cache(
            model_class=User,
            object_id=self.to_user_id,
        )


# hook up with listeners to invalidate cache
pre_delete.connect(receiver=invalidate_following_cache, sender=Friendship)
# 为什么缓存一般在 pre_delete 删除？post_delete后, instance就被删除了
post_save.connect(receiver=invalidate_following_cache, sender=Friendship)
# post_save: update / create 都会调用 save() => 删除对应的缓存
# post_save.connect(函数名, sender=Model模型名字)