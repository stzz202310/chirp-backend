from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save, pre_delete

from likes.models import Like
from tweets.constants import TweetModerationStatus, TWEET_MODERATION_STATUS_CHOICES
from tweets.listeners import push_tweet_to_cache
from utils.listeners import invalidate_object_cache
from utils.memcached_helper import MemcachedHelper
from utils.time_helpers import utc_now


class Tweet(models.Model):
    # user.tweet_set 等价于 Tweet.objects.filter(user=user)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text='who posts this tweet',
    )
    content = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    likes_count = models.IntegerField(default=0, null=True)
    comments_count = models.IntegerField(default=0, null=True)

    # 发帖时先 PENDING, Celery 异步调用 LLM 审核后回填 SAFE/FLAGGED
    moderation_status = models.IntegerField(
        default=TweetModerationStatus.PENDING,
        choices=TWEET_MODERATION_STATUS_CHOICES,
    )

    class Meta:
        index_together = (('user', 'created_at'),)
        ordering = ('user', '-created_at',)

    def __str__(self):
        return f'{self.created_at} {self.user}: {self.content}'

    @property
    def hours_to_now(self):
        return (utc_now() - self.created_at).seconds // 3600

    # @property     方法 1
    # def comments(self):
    #     return self.comment_set.all()
    #     return Comment.objects.filter(tweet=self)

    @property
    def like_set(self):
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(model=Tweet),
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