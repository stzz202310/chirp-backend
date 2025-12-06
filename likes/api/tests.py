from rest_framework import status

from testing.testcases import TestCase

LIKE_BASE_URL = '/api/likes/'
LIKE_CANCEL_URL = '/api/likes/cancel/'
COMMENT_LIST_API = '/api/comments/'
TWEET_LIST_API = '/api/tweets/'
TWEET_DETAIL_API = '/api/tweets/{}/'
NEWSFEED_LIST_API = '/api/newsfeeds/'


class LikeApiTests(TestCase):

    def setUp(self):
        self.clear_cache()
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

    def test_cancel(self):
        tweet = self.create_tweet(user=self.taotao)
        comment = self.create_comment(user=self.zhuzhu, tweet=tweet)
        like_comment_data = {'content_type': 'comment', 'object_id': comment.id}
        like_tweet_data = {'content_type': 'tweet', 'object_id': tweet.id}
        self.taotao_client.post(LIKE_BASE_URL, data=like_comment_data)
        self.zhuzhu_client.post(LIKE_BASE_URL, data=like_tweet_data)
        self.assertEqual(tweet.like_set.count(), 1)
        self.assertEqual(comment.like_set.count(), 1)

        # 1. login required
        response = self.anonymous_client.post(LIKE_CANCEL_URL, data=like_comment_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. get is not allowed
        response = self.taotao_client.get(LIKE_CANCEL_URL, data=like_comment_data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 3. wrong content_type
        response = self.taotao_client.post(LIKE_CANCEL_URL, data={
            'content_type': 'wrong',
            'object_id': comment.id,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. wrong object_id
        response = self.taotao_client.post(LIKE_CANCEL_URL, data={
            'content_type': 'comment',
            'object_id': -1,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 5. zhuzhu has not liked COMMENT before
        response = self.zhuzhu_client.post(LIKE_CANCEL_URL, data=like_comment_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], False)   # 0, 1
        self.assertEqual(tweet.like_set.count(), 1)
        self.assertEqual(comment.like_set.count(), 1)

        # 6. taotao successfully canceled COMMENT
        response = self.taotao_client.post(LIKE_CANCEL_URL, data=like_comment_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], True)
        self.assertEqual(tweet.like_set.count(), 1)
        self.assertEqual(comment.like_set.count(), 0)

        # 7. taotao has not liked TWEET before
        response = self.taotao_client.post(LIKE_CANCEL_URL, data=like_tweet_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], False)
        self.assertEqual(tweet.like_set.count(), 1)
        self.assertEqual(comment.like_set.count(), 0)

        # 8. zhuzhu successfully canceled TWEET
        response = self.zhuzhu_client.post(LIKE_CANCEL_URL, data=like_tweet_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], True)
        self.assertEqual(tweet.like_set.count(), 0)
        self.assertEqual(comment.like_set.count(), 0)

    def test_likes_in_comments_api(self):
        tweet = self.create_tweet(self.taotao)
        comment = self.create_comment(self.taotao, tweet)

        # 1. test anonymous
        data = {'tweet_id': tweet.id}
        response = self.anonymous_client.get(COMMENT_LIST_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comments'][0]['has_liked'], False)
        self.assertEqual(response.data['comments'][0]['likes_count'], 0)

        # 2. test COMMENT_LIST_API
        data = {'tweet_id': tweet.id}
        response = self.zhuzhu_client.get(COMMENT_LIST_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comments'][0]['has_liked'], False)
        self.assertEqual(response.data['comments'][0]['likes_count'], 0)
        self.create_like(user=self.zhuzhu, target=comment)
        response = self.zhuzhu_client.get(COMMENT_LIST_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comments'][0]['has_liked'], True)
        self.assertEqual(response.data['comments'][0]['likes_count'], 1)

        # 3. test TWEET_DETAIL_API
        self.create_like(user=self.taotao, target=comment)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.zhuzhu_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comments'][0]['has_liked'], True)
        self.assertEqual(response.data['comments'][0]['likes_count'], 2)

    def test_likes_in_tweets_api(self):
        tweet = self.create_tweet(self.taotao)

        # 1. test TWEET_DETAIL_API
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.zhuzhu_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_liked'], False)
        self.assertEqual(response.data['likes_count'], 0)
        self.create_like(user=self.zhuzhu, target=tweet)
        response = self.zhuzhu_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_liked'], True)
        self.assertEqual(response.data['likes_count'], 1)

        # 2. test TWEET_LIST_API
        data = {'user_id': self.taotao.id}
        response = self.zhuzhu_client.get(TWEET_LIST_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['has_liked'], True)
        self.assertEqual(response.data['results'][0]['likes_count'], 1)

        # 3. test NEWSFEED_LIST_API
        self.create_like(user=self.taotao, target=tweet)
        self.create_newsfeed(self.zhuzhu, tweet)
        response = self.zhuzhu_client.get(NEWSFEED_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['tweet']['has_liked'], True)
        self.assertEqual(response.data['results'][0]['tweet']['likes_count'], 2)

        # 4. test likes details via TWEET_DETAIL_API
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.zhuzhu_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['likes']), 2)
        self.assertEqual(response.data['likes'][0]['user']['id'], self.taotao.id)
        self.assertEqual(response.data['likes'][1]['user']['id'], self.zhuzhu.id)