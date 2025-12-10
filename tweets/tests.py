from datetime import timedelta

from testing.testcases import TestCase
from tweets.constants import TweetPhotoStatus
from tweets.models import TweetPhoto
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer
from utils.time_helpers import utc_now


class TweetTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.taotao = self.create_user('taotao')
        self.zhuzhu = self.create_user('zhuzhu')
        self.tweet = self.create_tweet(user=self.taotao, content='hello zhuzhu')

    def test_hours_to_now(self):
        self.tweet.created_at = utc_now() - timedelta(hours=10)
        self.tweet.save()
        self.assertEqual(self.tweet.hours_to_now, 10)

    def test_like_set(self):
        self.create_like(user=self.taotao, target=self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 1)

        self.create_like(user=self.taotao, target=self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 1)

        self.create_like(user=self.zhuzhu, target=self.tweet)
        self.assertEqual(self.tweet.like_set.count(), 2)

    def test_create_photo(self):
        # 测试可以成功创建 photo 的数据对象
        photo = TweetPhoto.objects.create(
            tweet=self.tweet,
            user=self.taotao,
        )
        self.assertEqual(photo.user, self.taotao)
        self.assertEqual(photo.status, TweetPhotoStatus.PENDING)
        self.assertEqual(self.tweet.tweetphoto_set.count(), 1)

    def test_cache_tweet_in_redis(self):
        tweet = self.create_tweet(user=self.taotao)
        # web server[redis client] <==> redis server
        conn = RedisClient.get_connection()
        serialized_data = DjangoModelSerializer.serialize(instance=tweet)
        conn.set(name=f'tweet:{tweet.id}', value=serialized_data)
        data = conn.get(f'tweet:not_exists')
        self.assertEqual(data, None)

        data = conn.get(f'tweet:{tweet.id}')
        cached_tweet = DjangoModelSerializer.deserialize(serialized_data=data)
        # 内容相同，但内存地址已经不是同一个了
        self.assertEqual(tweet, cached_tweet)