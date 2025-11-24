from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from comments.models import Comment
from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
COMMENT_DETAIL_URL = '/api/comments/{}/'


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

    def test_destroy(self):
        comment = self.create_comment(self.taotao, self.tweet)
        url = '{}{}/'.format(COMMENT_URL, comment.id)

        # 1. 匿名不可以删除
        response = self.anonymous_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. 非本人不能删除
        response = self.zhuzhu_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 3. 本人可以删除
        count = Comment.objects.count()
        response = self.taotao_client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), count - 1)

    def test_update(self):
        comment = self.create_comment(self.taotao, self.tweet, 'original')
        another_tweet = self.create_tweet(self.zhuzhu)
        # url = '{}{}/'.format(COMMENT_URL, comment.id)
        url = COMMENT_DETAIL_URL.format(comment.id)

        # 1. 匿名不可以更新
        response = self.anonymous_client.put(url, data={'content': 'new'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. 非本人不能更新
        response = self.zhuzhu_client.put(url, data={'content': 'new'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'You do not have permission to access this object.')
        comment.refresh_from_db()   # comment 不会自动更新
        self.assertEqual(comment.content, 'original')

        # 3. 只能更新 content，不能更新其他 fields 静默处理
        before_updated_at = comment.updated_at
        before_created_at = comment.created_at
        now = timezone.now()
        response = self.taotao_client.put(url, data={
            'content': 'new',
            'user_id': self.zhuzhu.id,
            'tweet_id': another_tweet.id,
            'created_at': now,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, 'new')
        self.assertEqual(comment.user, self.taotao)
        self.assertEqual(comment.tweet, self.tweet)
        self.assertEqual(comment.created_at, before_created_at)
        self.assertNotEqual(comment.created_at, now)
        self.assertNotEqual(comment.updated_at, before_updated_at)

    def test_list(self):
        pass
        # 1. 必须带 tweet_id
        response = self.anonymous_client.get(COMMENT_URL)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. 带了 tweet_id 可以访问 [一开始没有评论]
        response = self.anonymous_client.get(COMMENT_URL, data={
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 0)

        # 3. 评论按照时间顺序排序
        another_tweet = self.create_tweet(self.zhuzhu)
        self.create_comment(self.taotao, self.tweet, '1')
        self.create_comment(self.zhuzhu, self.tweet, '2')
        self.create_comment(self.zhuzhu, another_tweet, '3')
        response = self.anonymous_client.get(COMMENT_URL, data={
            'tweet_id': self.tweet.id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(response.data['comments'][0]['content'], '1')
        self.assertEqual(response.data['comments'][1]['content'], '2')

        # 4. 同时提供 user_id 和 tweet_id, 只有 tweet_id 会在 filter 中生效
        response = self.anonymous_client.get(COMMENT_URL, data={
            'tweet_id': self.tweet.id,
            'user_id': self.taotao.id,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 2)