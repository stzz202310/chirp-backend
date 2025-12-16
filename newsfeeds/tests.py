from newsfeeds.services import NewsFeedService
from testing.testcases import TestCase
from utils.redis_client import RedisClient
from twitter.cache import USER_NEWSFEEDS_PATTERN
from newsfeeds.models import NewsFeed
from newsfeeds.tasks import fanout_newsfeeds_main_task

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


class NewsFeedTaskTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.taotao = self.create_user(username='taotao')
        self.zhuzhu = self.create_user(username='zhuzhu')

    def test_fanout_main_task(self):
        # 1. zhuzhu 关注 taotao, Fanout taotao's tweet
        tweet = self.create_tweet(user=self.taotao, content='tweet1')
        self.create_friendship(from_user=self.zhuzhu, to_user=self.taotao)
        msg = fanout_newsfeeds_main_task(tweet_id=tweet.id, tweet_user_id=self.taotao.id)
        self.assertEqual(
            msg,
            '1 newsfeeds going to fanout, 1 batches created.'
        )
        self.assertEqual(NewsFeed.objects.count(), 1 + 1)
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual(len(cached_list), 1)
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.zhuzhu.id)
        self.assertEqual(len(cached_list), 1)

        # 2. 三个人 关注 taotao, Fanout taotao's tweet
        for i in range(2):
            user = self.create_user(username=f'user{i}')
            self.create_friendship(from_user=user, to_user=self.taotao)
        tweet = self.create_tweet(user=self.taotao, content='tweet2')
        msg = fanout_newsfeeds_main_task(tweet_id=tweet.id, tweet_user_id=self.taotao.id)
        self.assertEqual(
            msg,
            '3 newsfeeds going to fanout, 1 batches created.'
        )
        self.assertEqual(NewsFeed.objects.count(), 2 + 4)
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual(len(cached_list), 2)
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.zhuzhu.id)
        self.assertEqual(len(cached_list), 2)

        # 3. 五个人 关注 taotao, Fanout taotao's tweet
        for i in range(2):
            user = self.create_user(username=f'user{i+2}')
            self.create_friendship(from_user=user, to_user=self.taotao)
        tweet = self.create_tweet(user=self.taotao, content='tweet3')
        msg = fanout_newsfeeds_main_task(tweet_id=tweet.id, tweet_user_id=self.taotao.id)
        self.assertEqual(
            msg,
            '5 newsfeeds going to fanout, 2 batches created.'
        )
        self.assertEqual(NewsFeed.objects.count(), 2 + 4 + 6)
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual(len(cached_list), 3)
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.zhuzhu.id)
        self.assertEqual(len(cached_list), 3)