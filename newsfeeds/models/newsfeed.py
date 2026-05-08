from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save

from newsfeeds.listeners import push_newsfeed_to_cache
from tweets.models import Tweet
from utils.memcached_helper import MemcachedHelper


class NewsFeed(models.Model):
    # user: 能看到这条 tweet 的用户 (关注了发帖人), 而非 tweet 作者
    # user: 一般是 request.user, 不需要读取缓存
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    # [冗余]created_at = tweet.created_at，作为独立字段是为了支持 index_together
    created_at = models.DateTimeField()

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