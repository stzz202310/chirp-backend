from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import post_save, pre_delete

from comments.listeners import incr_comments_count, decr_comments_count
from likes.models import Like
from tweets.models import Tweet
from utils.memcached_helper import MemcachedHelper


class Comment(models.Model):
    """
    本版本实现基础评论功能:
    - 评论仅可针对某条 Tweet 发布
    - 不支持对其他评论进行回复 (禁止多级评论)
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    content = models.TextField(max_length=140)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # 需求: 在某个 Tweet 下排序所有 comments
        index_together = (('tweet', 'created_at'),)

    def __str__(self):
        return '{} - {} says {} at tweet {}'.format(
            self.created_at,
            self.user,
            self.content,
            self.tweet_id,
        )

    @property
    def like_set(self):
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(model=Comment),
            object_id=self.id,
        ).order_by('-created_at')

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(
            model_class=User,
            object_id=self.user_id,
        )


pre_delete.connect(receiver=decr_comments_count, sender=Comment)
post_save.connect(receiver=incr_comments_count, sender=Comment)