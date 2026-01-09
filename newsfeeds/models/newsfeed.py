"""
Deprecated
use newsfeeds.models.hbase_models.HBaseNewsFeed instead
"""

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save

from newsfeeds.listeners import push_newsfeed_to_cache
from tweets.models import Tweet
from utils.memcached_helper import MemcachedHelper


class NewsFeed(models.Model):
    # user: 不是存储谁发了这条 tweet，而是谁可以看到这条 tweet
    # user follow 了 tweet 的发帖人，所以 user 的新鲜事列表有这个帖子
    # user 一般是 request.user, 不需要读取缓存
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # [冗余]等于 tweet.created_at; 原因 必须是字段，才能 index_together
    # TODO [Myself] created_at 应该等于 tweet.created_at, 而不是 auto_now_add=True; 并增加相应的 unit test
    # iso格式: 2026-01-01 10:10:10.000000     NewsFeed.created_at      = tweet.created_at
    # int格式: 1767934515324687               HBaseNewsFeed.created_at = Tweet.timestamp

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


post_save.connect(receiver=push_newsfeed_to_cache, sender=NewsFeed)