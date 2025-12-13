from django.conf import settings
from rest_framework import status
from rest_framework.test import APIClient

from newsfeeds.models import NewsFeed
from newsfeeds.services import NewsFeedService
from testing.testcases import TestCase
from utils.paginations import EndlessPagination

NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.taotao = self.create_user('taotao')
        self.taotao_client = APIClient()
        self.taotao_client.force_authenticate(self.taotao)

        self.zhuzhu = self.create_user('zhuzhu')
        self.zhuzhu_client = APIClient()
        self.zhuzhu_client.force_authenticate(self.zhuzhu)

    def test_list(self):
        # 1. 需要登陆
        response = self.anonymous_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 2. 不能用 post
        response = self.taotao_client.post(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 3. 一开始啥都没有
        response = self.taotao_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)
        # 4. 自己发的信息是可以看到的
        self.taotao_client.post(POST_TWEETS_URL, data={'content': "Hello Zhuzhu!"})
        response = self.taotao_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        # 5. 关注之后可以看到别人发的
        self.taotao_client.post(FOLLOW_URL.format(self.zhuzhu.id))
        response = self.zhuzhu_client.post(
            path=POST_TWEETS_URL,
            data={'content': "Hello Taotao",}
        )
        posted_tweet_id = response.data['id']
        response = self.taotao_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['results'][0]['tweet']['id'], posted_tweet_id)

    def test_pagination(self):
        page_size = EndlessPagination.page_size
        followed_user = self.create_user(username='followed')
        newsfeeds = []
        for i in range(page_size * 2):
            tweet = self.create_tweet(user=followed_user)
            newsfeed = self.create_newsfeed(user=self.taotao, tweet=tweet)
            newsfeeds.append(newsfeed)
        newsfeeds = newsfeeds[::-1]

        # 1. pull the 1st page
        response = self.taotao_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_next_page'], True)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['results'][0]['id'], newsfeeds[0].id)
        self.assertEqual(response.data['results'][1]['id'], newsfeeds[1].id)
        self.assertEqual(
            response.data['results'][page_size - 1]['id'],
            newsfeeds[page_size - 1].id,
        )

        # 2. pull the 2nd page
        response = self.taotao_client.get(
            path=NEWSFEEDS_URL,
            data={'created_at__lt': newsfeeds[page_size - 1].created_at},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_next_page'], False)
        results = response.data['results']
        self.assertEqual(len(results), page_size)
        self.assertEqual(results[0]['id'], newsfeeds[0 + page_size].id)
        self.assertEqual(results[1]['id'], newsfeeds[1 + page_size].id)
        self.assertEqual(
            results[page_size - 1]['id'],
            newsfeeds[page_size - 1 + page_size].id,
        )

        # 3. pull latest newsfeed
        response = self.taotao_client.get(
            path=NEWSFEEDS_URL,
            data={'created_at__gt': newsfeeds[0].created_at},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 0)

        tweet = self.create_tweet(user=followed_user)
        new_newsfeed = self.create_newsfeed(user=self.taotao, tweet=tweet)
        response = self.taotao_client.get(
            path=NEWSFEEDS_URL,
            data={'created_at__gt': newsfeeds[0].created_at}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], new_newsfeed.id)

    def test_user_cache(self):
        # newsfeeds -> tweets -> users -> user profile
        profile = self.zhuzhu.profile
        profile.nickname = 'yaoyao'
        profile.save()

        self.assertEqual(self.taotao.username, 'taotao')
        self.create_newsfeed(user=self.zhuzhu, tweet=self.create_tweet(user=self.taotao))
        self.create_newsfeed(user=self.zhuzhu, tweet=self.create_tweet(user=self.zhuzhu))

        response = self.zhuzhu_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'zhuzhu')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'yaoyao')
        self.assertEqual(results[1]['tweet']['user']['username'], 'taotao')

        self.taotao.username = 'pipi'
        self.taotao.save()
        profile.nickname = 'miaomiaomiao'   # zhuzhu
        profile.save()

        response = self.zhuzhu_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'zhuzhu')
        self.assertEqual(results[0]['tweet']['user']['nickname'], 'miaomiaomiao')
        self.assertEqual(results[1]['tweet']['user']['username'], 'pipi')

    def test_tweet_cache(self):
        tweet = self.create_tweet(user=self.taotao, content='taotao tweet')
        self.create_newsfeed(user=self.zhuzhu, tweet=tweet)
        response = self.zhuzhu_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'taotao')
        self.assertEqual(results[0]['tweet']['content'], 'taotao tweet')

        # update username
        self.taotao.username = 'pipi'
        self.taotao.save()
        response = self.zhuzhu_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['user']['username'], 'pipi')

        # update content
        tweet.content = 'taotao tweet2'
        tweet.save()
        response = self.zhuzhu_client.get(NEWSFEEDS_URL)
        results = response.data['results']
        self.assertEqual(results[0]['tweet']['content'], 'taotao tweet2')

    def _paginate_to_get_newsfeeds(self, client):
        # paginate until the end 模拟用户上拉加载更多
        response = client.get(NEWSFEEDS_URL)
        results = response.data['results']
        while response.data['has_next_page']:
            created_at__lt = response.data['results'][-1]['created_at']
            response = client.get(
                path=NEWSFEEDS_URL,
                data={'created_at__lt': created_at__lt}
            )
            results.extend(response.data['results'])
        return results

    def test_redis_list_limit(self):
        list_limit = settings.REDIS_LIST_LENGTH_LIMIT
        page_size = EndlessPagination.page_size
        users = [self.create_user(username=f'user{i}') for i in range(5)]
        newsfeeds = []
        for i in range(list_limit + page_size):
            tweet = self.create_tweet(user=users[i % 5], content=f'feed{i}')
            feed = self.create_newsfeed(user=self.taotao, tweet=tweet)
            newsfeeds.append(feed)
        newsfeeds = newsfeeds[::-1]

        # 1. only cached list_limit objects
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=self.taotao.id)
        self.assertEqual(len(cached_newsfeeds), list_limit)
        queryset = NewsFeed.objects.filter(user=self.taotao)
        self.assertEqual(len(queryset), list_limit + page_size)

        results = self._paginate_to_get_newsfeeds(client=self.taotao_client)
        self.assertEqual(len(results), list_limit + page_size)
        for i in range(list_limit + page_size):
            self.assertEqual(newsfeeds[i].id, results[i]['id'])

        # 2. a followed user create a new tweet
        self.create_friendship(from_user=self.taotao, to_user=self.zhuzhu)
        new_tweet = self.create_tweet(user=self.zhuzhu, content='a new tweet')
        NewsFeedService.fanout_to_followers(tweet=new_tweet)

        def _test_newsfeeds_after_new_feed_pushed():
            results = self._paginate_to_get_newsfeeds(client=self.taotao_client)
            self.assertEqual(len(results), list_limit + page_size + 1)
            self.assertEqual(results[0]['tweet']['id'], new_tweet.id)
            for i in range(list_limit + page_size):
                self.assertEqual(newsfeeds[i].id, results[i + 1]['id'])

        _test_newsfeeds_after_new_feed_pushed()
        # cache expired
        self.clear_cache()
        _test_newsfeeds_after_new_feed_pushed()