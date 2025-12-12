from newsfeeds.services import NewsFeedService
from testing.testcases import TestCase
from utils.redis_client import RedisClient
from twitter.cache import USER_NEWSFEEDS_PATTERN

class NewsFeedServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.taotao = self.create_user(username='taotao')
        self.zhuzhu = self.create_user(username='zhuzhu')

    def test_get_user_newsfeeds(self):
        newsfeed_ids = []
        for i in range(3):
            tweet = self.create_tweet(user=self.zhuzhu)
            newsfeed = self.create_newsfeed(user=self.taotao, tweet=tweet)
            newsfeed_ids.append(newsfeed.id)
        newsfeed_ids = newsfeed_ids[::-1]

        # 1. cache miss
        RedisClient.clear()
        conn = RedisClient.get_connection()
        newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

        # 2. cache hit
        newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

        # 3. cache updated
        tweet = self.create_tweet(user=self.taotao)
        new_newsfeed = self.create_newsfeed(user=self.taotao, tweet=tweet)
        newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao)
        newsfeed_ids.insert(0, new_newsfeed.id)
        self.assertEqual([f.id for f in newsfeeds], newsfeed_ids)

    def test_create_new_newsfeed_before_get_cached_newsfeeds(self):
        tweet1 = self.create_tweet(user=self.taotao)
        newsfeed1 = self.create_newsfeed(user=self.taotao, tweet=tweet1)

        # 1. cache miss
        RedisClient.clear()
        conn = RedisClient.get_connection()
        key = USER_NEWSFEEDS_PATTERN.format(user_id=self.taotao.id)
        self.assertEqual(conn.exists(key), False)

        # 2. cache hit
        tweet2 = self.create_tweet(user=self.taotao)
        newsfeed2 = self.create_newsfeed(user=self.taotao, tweet=tweet2)
        self.assertEqual(conn.exists(key), True)

        newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual([f.id for f in newsfeeds], [newsfeed2.id, newsfeed1.id])