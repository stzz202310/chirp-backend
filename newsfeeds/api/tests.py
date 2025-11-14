from rest_framework import status
from rest_framework.test import APIClient

from testing.testcases import TestCase


NEWSFEEDS_URL = '/api/newsfeeds/'
POST_TWEETS_URL = '/api/tweets/'
FOLLOW_URL = '/api/friendships/{}/follow/'


class NewsFeedApiTests(TestCase):

    def setUp(self):
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
        self.assertEqual(len(response.data['newsfeeds']), 0)
        # 4. 自己发的信息是可以看到的
        self.taotao_client.post(POST_TWEETS_URL, data={'content': "Hello Zhuzhu!"})
        response = self.taotao_client.get(NEWSFEEDS_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['newsfeeds']), 1)
        # 5. 关注之后可以看到别人发的
        self.taotao_client.post(FOLLOW_URL.format(self.zhuzhu.id))
        response = self.zhuzhu_client.post(POST_TWEETS_URL, data={
            'content': "Hello Taotao",
        })
        posted_tweet_id = response.data['id']
        response = self.taotao_client.get(NEWSFEEDS_URL)
        self.assertEqual(len(response.data['newsfeeds']), 2)
        self.assertEqual(response.data['newsfeeds'][0]['tweet']['id'], posted_tweet_id)