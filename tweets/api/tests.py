from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from testing.testcases import TestCase
from tweets.constants import TWEET_PHOTOS_UPLOAD_LIMIT
from tweets.models import Tweet, TweetPhoto
from utils.paginations import EndlessPagination

TWEET_LIST_API = '/api/tweets/'
TWEET_CREATE_API = '/api/tweets/'
TWEET_RETRIEVE_API = '/api/tweets/{}/'


class TweetApiTest(TestCase):

    def setUp(self):
        super(TweetApiTest, self).setUp()
        self.user1, self.user1_client = self.create_user_and_client('user1', 'user1@zhuzhu.com')

        self.user2 = self.create_user('user2', 'user2@zhuzhu.com')
        self.user2_client = APIClient() # user2 未登录
        self.tweets2 = [self.create_tweet(user=self.user2) for _ in range(2)]

    def test_list_api(self):
        # 1 必须带 user_id
        response = self.anonymous_client.get(TWEET_LIST_API)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 2 正常 request
        response = self.anonymous_client.get(TWEET_LIST_API, data={'user_id': self.user1.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

        response = self.anonymous_client.get(TWEET_CREATE_API, data={'user_id': self.user2.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

        # 2_1 检测排序是按照新创建的在前面的顺序来的 '-created_at'
        self.assertEqual(response.data['results'][0]['id'], self.tweets2[1].id)
        self.assertEqual(response.data['results'][1]['id'], self.tweets2[0].id)

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
        response = self.user1_client.post(TWEET_CREATE_API, data={'content': '0' * 141})
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
        response = self.anonymous_client.get(url)
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
        self.assertEqual(response.data['comments'][0]['content'], 'user1 comment')
        self.assertEqual(response.data['comments'][1]['content'], 'user2 comment')

        # 3. tweet 里包含用户的头像和昵称
        profile = self.user1.profile
        self.assertEqual(response.data['user']['nickname'], profile.nickname)   # None
        self.assertEqual(response.data['user']['avatar_url'], profile.avatar)   # None

    def test_create_with_files(self):
        # 1. 上传空文件列表
        data = {'content': 'empty content', 'files': [],}
        response = self.user1_client.post(path=TWEET_CREATE_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TweetPhoto.objects.count(), 0)

        # 2. 上传单个文件
        file = SimpleUploadedFile(
            name='selfie.jpg',
            content=str.encode('selfie'),   # bytes 类型
            content_type='image/jpeg',
        )
        data = {'content': 'a selfie', 'files': [file]}
        response = self.user1_client.post(path=TWEET_CREATE_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['photo_urls']), 1)
        self.assertEqual('selfie' in response.data['photo_urls'][0], True)
        self.assertEqual(TweetPhoto.objects.count(), 1)

        # 3. 上传多个文件
        file1 = SimpleUploadedFile(
            name='selfie1.jpg',
            content=str.encode('selfie1'),
            content_type='image/jpeg',
        )
        file2 = SimpleUploadedFile(
            name='selfie2.jpg',
            content=str.encode('selfie2'),
            content_type='image/jpeg',
        )
        data = {'content': 'two selfies', 'files': [file1, file2],}
        response = self.user1_client.post(path=TWEET_CREATE_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data['photo_urls']), 2)
        self.assertEqual('selfie1' in response.data['photo_urls'][0], True)
        self.assertEqual('selfie2' in response.data['photo_urls'][1], True)
        self.assertEqual(TweetPhoto.objects.count(), 3)

        # 4. 从读取的 API 里确保已经包含了 photo 的地址
        retrieve_url = TWEET_RETRIEVE_API.format(response.data['id'])
        response = self.user1_client.get(retrieve_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['photo_urls']), 2)
        self.assertEqual('selfie1' in response.data['photo_urls'][0], True)
        self.assertEqual('selfie2' in response.data['photo_urls'][1], True)

        # 5. 测试上传超过 9个文件会失败
        files = [
            SimpleUploadedFile(
                name=f'selfie{i}.jpg',
                content=str.encode(f'selfie{i}'),
                content_type='image/jpeg',
            )
            for i in range(10)
        ]
        data = {'content': 'failed due to number of photos exceeded limit', 'files': files}
        response = self.user1_client.post(path=TWEET_CREATE_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data['errors']['message'][0],
            f'You can upload {TWEET_PHOTOS_UPLOAD_LIMIT} photos at most')
        self.assertEqual(TweetPhoto.objects.count(), 3)

    def test_pagination(self):
        page_size = EndlessPagination.page_size
        tweets = []

        # 1. create page_size*2 tweets
        for i in range(page_size * 2):
            tweets.append(self.create_tweet(user=self.user1, content=f'tweet{i}'))
        tweets = tweets[::-1]   # 倒序 {最新的帖子 tweets[0]}

        # 2. pull the first page
        response = self.user1_client.get(
            path=TWEET_LIST_API,
            data={'user_id': self.user1.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_next_page'], True)
        self.assertEqual(len(response.data['results']), page_size)
        for i in range(page_size):
            self.assertEqual(response.data['results'][i]['id'], tweets[i].id)

        # 3. pull the second page
        response = self.user1_client.get(
            path=TWEET_LIST_API,
            data={
                'user_id': self.user1.id,
                'created_at__lt': tweets[page_size - 1].created_at,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), page_size)
        for i in range(page_size):
            self.assertEqual(response.data['results'][i]['id'], tweets[i + page_size].id)

        # 4. pull [ALL] the latest tweets without pagination
        data = {'user_id': self.user1.id, 'created_at__gt':tweets[0].created_at}
        response = self.user1_client.get(path=TWEET_LIST_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 0)

        new_tweet = self.create_tweet(user=self.user1, content='a new tweet comes in')
        response = self.user1_client.get(path=TWEET_LIST_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], new_tweet.id)

        tweets.insert(0, new_tweet)
        for i in range(page_size):
            tweets.insert(0, self.create_tweet(user=self.user1, content=f'new tweet{i}'))
        response = self.user1_client.get(path=TWEET_LIST_API, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['has_next_page'], False)
        self.assertEqual(len(response.data['results']), page_size + 1)
        for i in range(page_size + 1):
            self.assertEqual(response.data['results'][i]['id'], tweets[i].id)