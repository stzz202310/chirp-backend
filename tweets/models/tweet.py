from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save, pre_delete

from likes.models import Like
from tweets.listeners import push_tweet_to_cache
from utils.listeners import invalidate_object_cache
from utils.memcached_helper import MemcachedHelper
from utils.time_helpers import utc_now


class Tweet(models.Model):
    # tweet_id: 不能默认是连续的，因为可能会删除帖子
    user = models.ForeignKey(   # user.tweet_set 等价于 Tweet.objects.filter(user=user)
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text='who posts this tweet',
    )   # 这篇帖子是谁发的
    content = models.CharField(max_length=255)  # 'abcde\0': \0表示字符串的结束
    created_at = models.DateTimeField(auto_now_add=True)

    # ⚠️ 新增的 field 一定要设置 null=True，否则 default = 0 会遍历整个表单去设置
    # 导致 Migration 过程非常慢，从而把整张表单锁死，正常用户无法创建新的 tweets
    # 历史 Tweet 的 likes_count 如何回填? 回填脚本: 遍历整个表单，把数据分批填上(bulk_update), 不会锁整张 Tweet 表
    likes_count = models.IntegerField(default=0, null=True)
    comments_count = models.IntegerField(default=0, null=True)

    class Meta:
        index_together = (('user', 'created_at'),) # show index from `tweets_tweet`
        ordering = ('user', '-created_at',) # 不会对数据库产生影响，只会影响 QuerySet

    def __str__(self):
        # 这里是你执行 print(tweet instance) 的时候会显示的内容
        return f'{self.created_at} {self.user}: {self.content}'

    @property
    def hours_to_now(self):
        # 不需要传额外参数的时候，可以用 @propert

        # 并不是数据库表中的真实字段 tweet.hours_to_now
        # datetime.now 不带时区信息，需要加上 utc 的时区信息
        return (utc_now() - self.created_at).seconds // 3600

    # @property
    # def comments(self):
    #     return self.comment_set.all()
    #     return Comment.objects.filter(tweet=self)

    @property
    def like_set(self):
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(Tweet),
            object_id=self.id,
        ).order_by('-created_at')

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(
            model_class=User,
            object_id=self.user_id,
        )

    @property
    def timestamp(self):
        return int(self.created_at.timestamp() * 1000000)


post_save.connect(receiver=invalidate_object_cache, sender=Tweet)
pre_delete.connect(receiver=invalidate_object_cache, sender=Tweet)
post_save.connect(receiver=push_tweet_to_cache, sender=Tweet)
# TODO [Myself] 增加[删除Tweet的API接口], 并思考如何处理 redis {user_id:[tweets] / [newsfeeds]}?
# 1. 软删除标记(soft delete, 类似回收站) has_deleted
# 2. 删除Tweet => 删除相应的newsfeeds[fanout 删除?]
# 3a. redis {user_id:[tweet_ids] / [newsfeed_ids]} 只保存 [ids]
# 3b. 删除相应的 redis cache
# 读取Tweet|Newsfeed列表: 跳过已经删除的Tweet vs 从数据库加载数据