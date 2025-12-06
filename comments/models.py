from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models

from likes.models import Like
from tweets.models import Tweet
from utils.memcached_helper import MemcachedHelper


class Comment(models.Model):
    """
    这个版本中，我们先实现一个比较简单的评论
    评论只评论在某个Tweet上, 不能评论别人的评论
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    content = models.TextField(max_length=140)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # 需求: 在某个 Tweet 下排序所有 comments [comment.like_set]
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
            content_type=ContentType.objects.get_for_model(Comment),
            object_id=self.id,
        ).order_by('-created_at')

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(
            model_class=User,
            object_id=self.user_id,
        )