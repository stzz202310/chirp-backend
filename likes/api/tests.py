from rest_framework import status

from testing.testcases import TestCase

LIKE_BASE_URL = '/api/likes/'

class LikeApiTests(TestCase):

    def setUp(self):
        self.taotao, self.taotao_client = self.create_user_and_client(username='taotao')
        self.zhuzhu, self.zhuzhu_client = self.create_user_and_client(username='zhuzhu')

    def test_tweet_likes(self):
        tweet = self.create_tweet(user=self.taotao)
        data = {'content_type': 'tweet', 'object_id': tweet.id}

        # 1. anonymous is not allowed
        response = self.anonymous_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. get is not allowed
        response = self.taotao_client.get(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 3. wrong content_type
        response = self.taotao_client.post(LIKE_BASE_URL, data={
            'content_type': 'tweet_wrong',
            'object_id': tweet.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('content_type' in response.data['errors'], True)

        # 4. wrong object_id
        response = self.taotao_client.post(LIKE_BASE_URL, data={
            'content_type': 'tweet',
            'object_id': -1,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('object_id' in response.data['errors'], True)

        # 5. post success
        response = self.taotao_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(tweet.like_set.count(), 1)

        # 6. duplicate likes
        self.taotao_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)  # 静默处理
        self.assertEqual(tweet.like_set.count(), 1)
        self.zhuzhu_client.post(LIKE_BASE_URL, data)
        self.assertEqual(tweet.like_set.count(), 2)

    def test_comment_likes(self):
        tweet = self.create_tweet(user=self.taotao)
        comment = self.create_comment(user=self.zhuzhu, tweet=tweet)
        data = {'content_type': 'comment', 'object_id': comment.id}

        # 1. anonymous is not allowed
        response = self.anonymous_client.post(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. get is not allowed
        response = self.taotao_client.get(LIKE_BASE_URL, data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 3. wrong content_type
        response = self.taotao_client.post(LIKE_BASE_URL, data={
            'content_type': 'comment_wrong',
            'object_id': comment.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('content_type' in response.data['errors'], True)

        # 4. wrong object_id
        response = self.taotao_client.post(LIKE_BASE_URL, data={
            'content_type': 'comment',
            'object_id': -1,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('object_id' in response.data['errors'], True)

        # 5. post success
        response = self.taotao_client.post(LIKE_BASE_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(comment.like_set.count(), 1)

        # 6. duplicate likes
        response = self.taotao_client.post(LIKE_BASE_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED) # 静默处理
        self.assertEqual(comment.like_set.count(), 1)
        self.zhuzhu_client.post(LIKE_BASE_URL, data=data)
        self.assertEqual(comment.like_set.count(), 2)
