from rest_framework import status
from rest_framework.test import APIClient

from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'


class CommentAPITest(TestCase):

    def setUp(self):
        self.taotao = self.create_user('taotao')
        self.taotao_client = APIClient()
        self.taotao_client.force_authenticate(user=self.taotao)

        self.zhuzhu = self.create_user('zhuzhu')
        self.zhuzhu_client = APIClient()
        self.zhuzhu_client.force_authenticate(user=self.zhuzhu)

        self.tweet = self.create_tweet(user=self.taotao)

    def test_create(self):
        # 1. 匿名用户不可以创建 tweet
        response = self.anonymous_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. 啥参数都没带不行
        response = self.taotao_client.post(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. 只带 tweet_id 不行
        response = self.taotao_client.post(COMMENT_URL, data={'tweet_id': self.tweet.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. 只带 content 不行
        response = self.taotao_client.post(COMMENT_URL, data={'content': '1'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 5. content 太长不行
        response = self.taotao_client.post(COMMENT_URL, data={
            'tweet_id': self.tweet.id,
            'content': '1' * 141,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('content' in response.data.get('errors'), True)

        # 6. tweet_id 和 content 都带才行
        response = self.taotao_client.post(COMMENT_URL, data={
            'tweet_id': self.tweet.id,
            'content': '1',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['id'], self.taotao.id)
        self.assertEqual(response.data.get('tweet_id'), self.tweet.id)
        self.assertEqual(response.data.get('content'), '1')
