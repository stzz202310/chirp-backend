from django.contrib.auth.models import User
from django.db import models

from tweets.models import Tweet
from utils.memcached_helper import MemcachedHelper


class NewsFeed(models.Model):
    # 注意: user follow 了 tweet 的发帖人，所以 user's newsfeeds 有这个帖子
    # user 是 request.user, 不需要缓存
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # [冗余]等于tweet.created_at; 原因 必须是字段，才能 index_together

    class Meta:
        index_together = (('user', 'created_at'),)
        unique_together = (('user', 'tweet'),)
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.created_at} inbox of {self.user}: {self.tweet}'

    @property
    def cached_tweet(self):
        return MemcachedHelper.get_object_through_cache(
            model_class=Tweet,
            object_id=self.tweet_id,
        )