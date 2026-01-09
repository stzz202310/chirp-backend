from datetime import timedelta

from testing.testcases import TestCase
from tweets.constants import TweetPhotoStatus
from tweets.models import TweetPhoto
from tweets.services import TweetService
from twitter.cache import USER_TWEETS_PATTERN
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer
from utils.time_helpers import utc_now


class TweetTests(TestCase):

    def setUp(self):
        super(TweetTests, self).setUp()
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


class TweetServiceTests(TestCase):

    def setUp(self):
        super(TweetServiceTests, self).setUp()
        self.taotao = self.create_user(username='taotao')

    def test_get_user_tweets(self):
        tweet_ids = []
        for i in range(3):
            tweet = self.create_tweet(user=self.taotao, content=f'tweet{i}')
            tweet_ids.append(tweet.id)
        tweet_ids = tweet_ids[::-1]

        # 1. cache miss
        self.clear_cache()
        tweets = TweetService.get_cached_tweets(user_id=self.taotao.id)
        self.assertEqual([tweet.id for tweet in tweets], tweet_ids)

        # 2. cache hit
        tweets = TweetService.get_cached_tweets(user_id=self.taotao.id)
        self.assertEqual([tweet.id for tweet in tweets], tweet_ids)

        # 3. cache updated
        new_tweet = self.create_tweet(user=self.taotao, content='new tweet')
        tweets = TweetService.get_cached_tweets(user_id=self.taotao.id)
        tweet_ids.insert(0, new_tweet.id)
        self.assertEqual([tweet.id for tweet in tweets], tweet_ids)

    def test_create_new_tweet_before_get_cached_tweets(self):
        tweet1 = self.create_tweet(user=self.taotao, content='tweet1')

        # 1. cache miss
        self.clear_cache()
        conn = RedisClient.get_connection()
        key = USER_TWEETS_PATTERN.format(user_id=self.taotao.id)
        self.assertEqual(conn.exists(key), False)

        # 2. cache hit
        tweet2 = self.create_tweet(user=self.taotao, content='tweet2')
        self.assertEqual(conn.exists(key), True)

        tweets = TweetService.get_cached_tweets(user_id=self.taotao.id)
        self.assertEqual(
            [tweet.id for tweet in tweets],
            [tweet2.id, tweet1.id])