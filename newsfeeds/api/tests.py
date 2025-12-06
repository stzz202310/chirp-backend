from rest_framework import status
from rest_framework.test import APIClient

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