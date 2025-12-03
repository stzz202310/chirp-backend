from rest_framework import status
from rest_framework.test import APIClient

from testing.testcases import TestCase
from tweets.models import Tweet

# 注意结尾要加 '/', 要不然会产生 301 redirect
TWEET_LIST_API = '/api/tweets/'
TWEET_CREATE_API = '/api/tweets/'
TWEET_RETRIEVE_API = '/api/tweets/{}/'


class TweetApiTest(TestCase):

    def setUp(self):
        self.user1 = self.create_user('user1', 'user1@zhuzhu.com')
        self.tweets1 = [
            self.create_tweet(self.user1)
            for i in range(3)
        ]
        self.user1_client = APIClient()     # 创建一个测试用的客户端
        # user1_client 在访问任何 API 时，都以 user1 的身份登录
        self.user1_client.force_authenticate(self.user1)

        self.user2 = self.create_user('user2', 'user2@zhuzhu.com')
        self.tweets2 = [
            self.create_tweet(self.user2)
            for i in range(2)
        ]
        self.user2_client = APIClient()

    def test_list_api(self):
        # 1 必须带 user_id
        response = self.anonymous_client.get(TWEET_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 2 正常 request
        response = self.anonymous_client.get(TWEET_LIST_API, data={'user_id': self.user1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['tweets']), 3)

        response = self.anonymous_client.get(TWEET_CREATE_API, data={'user_id': self.user2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['tweets']), 2)

        # 2_1 检测排序是按照新创建的在前面的顺序来的 '-created_at'
        self.assertEqual(response.data['tweets'][0]['id'], self.tweets2[1].id)
        self.assertEqual(response.data['tweets'][1]['id'], self.tweets2[0].id)

    def test_create_api(self):
        # 1 必须登陆
        response = self.anonymous_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.user2_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2 必须带 content
        response = self.user1_client.post(TWEET_CREATE_API)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 2_1 content 不能太短
        response = self.user1_client.post(TWEET_CREATE_API, data={'content': '1'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 2_2 content 不能太长
        response = self.user1_client.post(TWEET_CREATE_API, data={
            'content': '0' * 141,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 3 正常发帖
        tweet_count = Tweet.objects.count()
        response = self.user1_client.post(TWEET_CREATE_API, data={
            'content': 'Good morning ZhuZhu, this is my first tweet.',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['id'], self.user1.id)
        self.assertEqual(Tweet.objects.count(), tweet_count + 1)

    def test_retrieve(self):
        # 1. tweet with id=-1 does not exist
        url = TWEET_RETRIEVE_API.format(-1)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # 2. 获取某个 tweet 的时候会一起把 comments 也拿下
        tweet = self.create_tweet(self.user1)
        url = TWEET_RETRIEVE_API.format(tweet.id)
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 0)

        self.create_comment(self.user1, tweet, 'user1 comment')
        self.create_comment(self.user2, tweet, 'user2 comment')
        self.create_comment(self.user1, self.create_tweet(self.user1), 'taotao')
        self.create_comment(self.user1, self.create_tweet(self.user2), 'zhuzhu')
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 2)

        # 3. tweet 里包含用户的头像和昵称
        profile = self.user1.profile
        self.assertEqual(response.data['user']['nickname'], profile.nickname)
        self.assertEqual(response.data['user']['avatar_url'], None)