from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from comments.models import Comment
from testing.testcases import TestCase

COMMENT_LIST_API = '/api/comments/'
COMMENT_DETAIL_API = '/api/comments/{}/'
TWEET_LIST_API = '/api/tweets/'
TWEET_DETAIL_API = '/api/tweets/{}/'
NEWSFEED_LIST_API = '/api/newsfeeds/'


class CommentAPITest(TestCase):

    def setUp(self):
        self.clear_cache()
        self.taotao, self.taotao_client = self.create_user_and_client(username='taotao')
        self.zhuzhu, self.zhuzhu_client = self.create_user_and_client(username='zhuzhu')

        self.tweet_taotao = self.create_tweet(user=self.taotao)
        self.tweet_zhuzhu = self.create_tweet(user=self.zhuzhu)

    def test_create(self):
        # 1. 匿名用户不可以创建 tweet
        response = self.anonymous_client.post(COMMENT_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. 啥参数都没带不行
        response = self.taotao_client.post(COMMENT_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. 只带 tweet_id 不行
        response = self.taotao_client.post(COMMENT_LIST_API, data={'tweet_id': self.tweet_taotao.id})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 4. 只带 content 不行
        response = self.taotao_client.post(COMMENT_LIST_API, data={'content': '1'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 5. content 太长不行
        response = self.taotao_client.post(COMMENT_LIST_API, data={
            'tweet_id': self.tweet_taotao.id,
            'content': '1' * 141,
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual('content' in response.data.get('errors'), True)

        # 6. tweet_id 和 content 都带才行
        response = self.taotao_client.post(COMMENT_LIST_API, data={
            'tweet_id': self.tweet_taotao.id,
            'content': '1',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['id'], self.taotao.id)
        self.assertEqual(response.data.get('tweet_id'), self.tweet_taotao.id)
        self.assertEqual(response.data.get('content'), '1')

    def test_destroy(self):
        comment_taotao = self.create_comment(user=self.taotao, tweet=self.tweet_taotao)
        comment_zhuzhu = self.create_comment(user=self.zhuzhu, tweet=self.tweet_taotao)
        url_comment_taotao = COMMENT_DETAIL_API.format(comment_taotao.id)
        url_comment_zhuzhu = COMMENT_DETAIL_API.format(comment_zhuzhu.id)
        count = Comment.objects.count()

        # 1. 匿名不可以删除
        response = self.anonymous_client.delete(url_comment_taotao)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. 非{评论作者 OR 推特作者}不能删除
        response = self.zhuzhu_client.delete(url_comment_taotao)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'You do not have permission to delete this object.')

        # 3. 评论作者 可以删除
        response = self.taotao_client.delete(url_comment_taotao)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), count - 1)

        # 4. 推特作者 可以删除
        response = self.taotao_client.delete(url_comment_zhuzhu)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Comment.objects.count(), count - 2)

    def test_update(self):
        comment_zhuzhu = self.create_comment(user=self.zhuzhu, tweet=self.tweet_taotao, content='original')
        # url = '{}{}/'.format(COMMENT_URL, comment.id)
        url = COMMENT_DETAIL_API.format(comment_zhuzhu.id)

        # 1. 匿名不可以更新
        response = self.anonymous_client.put(url, data={'content': 'new'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 2. 非本人不能更新 [推特作者不能更新]
        response = self.taotao_client.put(url, data={'content': 'new'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['detail'], 'You do not have permission to access this object.')
        comment_zhuzhu.refresh_from_db()   # comment 不会自动更新
        self.assertEqual(comment_zhuzhu.content, 'original')

        # 3. 只能更新 content，不能更新其他 fields 静默处理
        before_updated_at = comment_zhuzhu.updated_at
        before_created_at = comment_zhuzhu.created_at
        now = timezone.now()
        response = self.zhuzhu_client.put(url, data={
            'content': 'new',
            'user_id': self.taotao.id,
            'tweet_id': self.tweet_zhuzhu.id,
            'created_at': now,
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment_zhuzhu.refresh_from_db()
        self.assertEqual(comment_zhuzhu.content, 'new')
        self.assertEqual(comment_zhuzhu.user, self.zhuzhu)
        self.assertEqual(comment_zhuzhu.tweet, self.tweet_taotao)
        self.assertEqual(comment_zhuzhu.created_at, before_created_at)
        self.assertNotEqual(comment_zhuzhu.created_at, now)
        self.assertNotEqual(comment_zhuzhu.updated_at, before_updated_at)

    def test_list(self):
        # 1. 必须带 tweet_id
        response = self.anonymous_client.get(COMMENT_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. 带了 tweet_id 可以访问 [0条评论]
        response = self.anonymous_client.get(
            path=COMMENT_LIST_API,
            data={'tweet_id': self.tweet_taotao.id,}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 0)

        # 3. 评论按照时间顺序排序
        self.create_comment(user=self.taotao, tweet=self.tweet_taotao, content='1')
        self.create_comment(user=self.zhuzhu, tweet=self.tweet_taotao, content='2')
        self.create_comment(user=self.zhuzhu, tweet=self.tweet_zhuzhu, content='3')
        response = self.anonymous_client.get(
            path = COMMENT_LIST_API,
            data={'tweet_id': self.tweet_taotao.id,}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 2)
        self.assertEqual(response.data['comments'][0]['content'], '1')
        self.assertEqual(response.data['comments'][1]['content'], '2')

        # 4. 同时提供 user_id 和 tweet_id, 只有 tweet_id 会在 filter 中生效
        response = self.anonymous_client.get(
            path = COMMENT_LIST_API,
            data={'tweet_id': self.tweet_taotao.id, 'user_id': self.taotao.id,}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['comments']), 2)

    def test_comments_count(self):
        # 1. test TWEET_DETAIL_API
        tweet = self.create_tweet(user=self.taotao)
        url = TWEET_DETAIL_API.format(tweet.id)
        response = self.zhuzhu_client.get(path=url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['comments_count'], 0)

        # 2. test TWEET_LIST_API
        self.create_comment(user=self.taotao, tweet=tweet)
        data = {'user_id': self.taotao.id}
        response = self.zhuzhu_client.get(path=TWEET_LIST_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['comments_count'], 1)

        # 3. test NEWSFEED_LIST_API
        self.create_comment(user=self.zhuzhu, tweet=tweet)
        self.create_newsfeed(user=self.zhuzhu, tweet=tweet)
        response = self.zhuzhu_client.get(path=NEWSFEED_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['results'][0]['tweet']['comments_count'], 2)

    def test_comments_count_with_cache(self):
        # 1. 初始化，0条评论
        tweet_url = TWEET_DETAIL_API.format(self.tweet_taotao.id)
        response = self.taotao_client.get(path=tweet_url)
        self.assertEqual(self.tweet_taotao.comments_count, 0)
        self.assertEqual(response.data['comments_count'], 0)

        # 2. 增加 2条评论
        data = {'tweet_id': self.tweet_taotao.id, 'content': 'a comment'}
        for i in range(2):
            _, client = self.create_user_and_client(username=f'user{i}')
            response = client.post(path=COMMENT_LIST_API, data=data)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            response = client.get(path=tweet_url)
            self.assertEqual(response.data['comments_count'], i + 1)
            self.tweet_taotao.refresh_from_db()
            self.assertEqual(self.tweet_taotao.comments_count, i + 1)

        # 3. 增加 第3条评论
        comment_data = self.zhuzhu_client.post(path=COMMENT_LIST_API, data=data).data
        response = self.zhuzhu_client.get(path=tweet_url)
        self.assertEqual(response.data['comments_count'], 3)
        self.tweet_taotao.refresh_from_db()
        self.assertEqual(self.tweet_taotao.comments_count, 3)

        # 4. update comment shouldn't update ['comments_count']
        #    if not created: return
        comment_url = COMMENT_DETAIL_API.format(comment_data['id'])
        response = self.zhuzhu_client.put(path=comment_url, data={'content': 'updated'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.zhuzhu_client.get(path=tweet_url)
        self.assertEqual(response.data['comments_count'], 3)
        self.tweet_taotao.refresh_from_db()
        self.assertEqual(self.tweet_taotao.comments_count, 3)

        # 5. delete a comment will update ['comments_count']
        response = self.zhuzhu_client.delete(path=comment_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.taotao_client.get(path=tweet_url)
        self.assertEqual(response.data['comments_count'], 2)
        self.tweet_taotao.refresh_from_db()
        self.assertEqual(self.tweet_taotao.comments_count, 2)