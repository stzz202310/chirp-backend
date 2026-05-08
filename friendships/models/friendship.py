from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save, pre_delete

from friendships.listeners import invalidate_following_cache
from utils.memcached_helper import MemcachedHelper


class Friendship(models.Model):
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
            ('from_user', 'created_at'), # 关注列表 from_user=我: 获取 我关注的所有人，按照关注时间排序
            ('to_user', 'created_at'),   # 粉丝列表 to_user=我:   获取 关注我的所有人，按照关注时间排序
        )
        unique_together = (('from_user', 'to_user'),)
        ordering = ('-created_at',)

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


# 为什么缓存一般在 pre_delete 删除？post_delete后, instance就被删除了
pre_delete.connect(receiver=invalidate_following_cache, sender=Friendship)
post_save.connect(receiver=invalidate_following_cache, sender=Friendship)