from django.contrib.auth.models import User

from django_hbase import models
from tweets.models import Tweet
from utils.memcached_helper import MemcachedHelper


class HBaseNewsFeed(models.HBaseModel):
    user_id = models.IntegerField(reverse=True)
    created_at = models.TimestampField()
    tweet_id = models.IntegerField(column_family='cf')

    class Meta:
        table_name = 'twitter_newsfeeds'
        row_key = ('user_id', 'created_at')

    def __str__(self):
        return f'{self.created_at} inbox of {self.user_id}: {self.tweet_id}'

    @property
    def cached_tweet(self):
        return MemcachedHelper.get_object_through_cache(
            model_class=Tweet,
            object_id=self.tweet_id,
        )

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(
            model_class=User,
            object_id=self.user_id,
        )