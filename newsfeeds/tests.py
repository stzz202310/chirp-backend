from newsfeeds.services import NewsFeedService
from newsfeeds.tasks import fanout_newsfeeds_main_task
from testing.testcases import TestCase
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_client import RedisClient


class NewsFeedServiceTests(TestCase):

    def setUp(self):
        super(NewsFeedServiceTests, self).setUp()
        self.taotao = self.create_user(username='taotao')
        self.zhuzhu = self.create_user(username='zhuzhu')

    def test_get_user_newsfeeds(self):
        newsfeed_timestamps = []
        for i in range(3):
            tweet = self.create_tweet(user=self.zhuzhu)
            newsfeed = self.create_newsfeed(user=self.taotao, tweet=tweet)
            newsfeed_timestamps.append(newsfeed.created_at)
            self.assertIn(newsfeed.created_at, [tweet.created_at, tweet.timestamp])
        newsfeed_timestamps = newsfeed_timestamps[::-1]

        # 1. cache miss
        self.clear_cache()
        newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual([f.created_at for f in newsfeeds], newsfeed_timestamps)

        # 2. cache hit
        newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual([f.created_at for f in newsfeeds], newsfeed_timestamps)

        # 3. cache updated
        tweet = self.create_tweet(user=self.taotao)
        new_newsfeed = self.create_newsfeed(user=self.taotao, tweet=tweet)
        newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        newsfeed_timestamps.insert(0, new_newsfeed.created_at)
        self.assertEqual([f.created_at for f in newsfeeds], newsfeed_timestamps)

    def test_create_new_newsfeed_before_get_cached_newsfeeds(self):
        tweet1 = self.create_tweet(user=self.taotao)
        newsfeed1 = self.create_newsfeed(user=self.taotao, tweet=tweet1)

        # 1. cache miss
        # ❌ RedisClient.clear() 测试环境: Redis/Gatekeeper/Celery 的数据都会被清空
        self.clear_cache()
        conn = RedisClient.get_connection()
        key = USER_NEWSFEEDS_PATTERN.format(user_id=self.taotao.id)
        self.assertEqual(conn.exists(key), False)

        # 2. redis_helper.push_objects 不重建冷缓存 (新行为): 创建新 newsfeed 后, 缓存仍不存在
        tweet2 = self.create_tweet(user=self.taotao)
        newsfeed2 = self.create_newsfeed(user=self.taotao, tweet=tweet2)
        self.assertEqual(conn.exists(key), False)

        newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual([f.id for f in newsfeeds], [newsfeed2.id, newsfeed1.id])


class NewsFeedTaskTests(TestCase):

    def setUp(self):
        super(NewsFeedTaskTests, self).setUp()
        self.taotao = self.create_user(username='taotao')
        self.zhuzhu = self.create_user(username='zhuzhu')

    def test_fanout_main_task(self):
        # 1. zhuzhu 关注 taotao, Fanout taotao's tweet
        tweet = self.create_tweet(user=self.taotao, content='tweet1')
        self.create_friendship(from_user=self.zhuzhu, to_user=self.taotao)
        msg = fanout_newsfeeds_main_task(
            tweet_id=tweet.id,
            created_at=NewsFeedService.created_at(tweet=tweet),
            tweet_user_id=self.taotao.id,
        )
        self.assertEqual(1 + 1, NewsFeedService.count())
        self.assertEqual(msg,'1 newsfeeds going to fanout, 1 batches created.')
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual(len(cached_list), 1)
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.zhuzhu.id)
        self.assertEqual(len(cached_list), 1)

        # 2. 三个人 关注 taotao, Fanout taotao's tweet
        for i in range(2):
            user = self.create_user(username=f'user{i}')
            self.create_friendship(from_user=user, to_user=self.taotao)
        tweet = self.create_tweet(user=self.taotao, content='tweet2')
        msg = fanout_newsfeeds_main_task(
            tweet_id=tweet.id,
            created_at=NewsFeedService.created_at(tweet=tweet),
            tweet_user_id=self.taotao.id,
        )
        self.assertEqual(4 + 2, NewsFeedService.count())
        self.assertEqual(msg,'3 newsfeeds going to fanout, 1 batches created.')
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual(len(cached_list), 2)
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.zhuzhu.id)
        self.assertEqual(len(cached_list), 2)

        # 3. 五个人 关注 taotao, Fanout taotao's tweet
        for i in range(2):
            user = self.create_user(username=f'user{i+2}')
            self.create_friendship(from_user=user, to_user=self.taotao)
        tweet = self.create_tweet(user=self.taotao, content='tweet3')
        msg = fanout_newsfeeds_main_task(
            tweet_id=tweet.id,
            created_at=NewsFeedService.created_at(tweet=tweet),
            tweet_user_id=self.taotao.id,
        )
        self.assertEqual(6 + 4 + 2, NewsFeedService.count())
        self.assertEqual(msg,'5 newsfeeds going to fanout, 2 batches created.')
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual(len(cached_list), 3)
        cached_list = NewsFeedService.get_cached_newsfeeds(user_id=self.zhuzhu.id)
        self.assertEqual(len(cached_list), 3)