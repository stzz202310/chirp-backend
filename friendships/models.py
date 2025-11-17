from django.db import models
from django.contrib.auth.models import User


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
            # ('from_user_id', 'created_at'), 也可以
            ('from_user', 'created_at'), # 关注列表 from_user=我: 获取我关注的所有人，按照关注时间排序
            ('to_user', 'created_at'),   # 粉丝列表 to_user=我:   获取关注我的所有人，按照关注时间排序
        )
        unique_together = (('from_user', 'to_user'),)   # 数据库层面 防止 重复关注
        ordering = ('-created_at',) # 对所有的查询结果 QuerySet 都有效

    def __str__(self):
        return '{} followed {}'.format(self.from_user_id, self.to_user_id)