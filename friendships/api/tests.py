from rest_framework import status
from rest_framework.test import APIClient

from friendships.models import Friendship
from testing.testcases import TestCase


FOLLOW_URL = '/api/friendships/{}/follow/'
UNFOLLOW_URL = '/api/friendships/{}/unfollow/'
FOLLOWERS_URL = '/api/friendships/{}/followers/'
FOLLOWINGS_URL = '/api/friendships/{}/followings/'


class FriendshipApiTests(TestCase):

    def setUp(self):
        self.taotao = self.create_user('taotao')
        self.taotao_client = APIClient()
        self.taotao_client.force_authenticate(self.taotao)

        self.zhuzhu=self.create_user('zhuzhu')
        self.zhuzhu_client = APIClient()
        self.zhuzhu_client.force_authenticate(self.zhuzhu)

        # create followings and followers for zhuzhu
        for i in range(2):
            follower = self.create_user(f'zhuzhu_follower{i}')
            Friendship.objects.create(from_user=follower,to_user=self.zhuzhu)
        for i in range(3):
            following = self.create_user(f'zhuzhu_following{i}')
            Friendship.objects.create(from_user=self.zhuzhu,to_user=following)

    def test_follow(self):
        url = FOLLOW_URL.format(self.taotao.id)

        # 1. 需要登陆才能 follow 别人
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 2. 需要用 get 来 follow
        response = self.zhuzhu_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 3. 不可以 follow 自己
        response = self.taotao_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # 4. follow 成功
        response = self.zhuzhu_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual('created_at' in response.data, True)
        self.assertEqual('user' in response.data, True)
        self.assertEqual(response.data['user']['id'], self.taotao.id)
        self.assertEqual(response.data['user']['username'], self.taotao.username)
        # 5. 重复 follow
        response = self.zhuzhu_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # 6. 反向关注会创建新的数据
        count = Friendship.objects.count()
        url = FOLLOW_URL.format(self.zhuzhu.id)
        response = self.taotao_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Friendship.objects.count(), count + 1)
        # 7. follow 不存在的用户
        url = FOLLOW_URL.format(1000)
        response = self.taotao_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unfollow(self):
        url = UNFOLLOW_URL.format(self.taotao.id)

        # 1. 需要登陆才能 unfollow 别人
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 2. 不能用 get 来 unfollow 别人
        response = self.zhuzhu_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 3. 不能 unfollow 自己
        response = self.taotao_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # 4. unfollow 成功
        Friendship.objects.create(from_user=self.zhuzhu, to_user=self.taotao)
        count = Friendship.objects.count()
        response = self.zhuzhu_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 1)
        self.assertEqual(Friendship.objects.count(), count - 1)
        # 5. 没有 follow 的情况下 unfollow 静默处理
        count = Friendship.objects.count()
        response = self.zhuzhu_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 0)
        self.assertEqual(Friendship.objects.count(), count)
        # 6. unfollow 不存在的用户
        url = UNFOLLOW_URL.format(1000)
        response = self.taotao_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_followings(self):
        url = FOLLOWINGS_URL.format(self.zhuzhu.id)
        # 1. post is not allowed
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 2. get is ok
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['followings']), 3)
        # 3. 确保按照时间倒序
        ts0 = response.data['followings'][0]['created_at']
        ts1 = response.data['followings'][1]['created_at']
        ts2 = response.data['followings'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)
        self.assertEqual(
            response.data['followings'][0]['user']['username'],
            'zhuzhu_following2',
        )
        self.assertEqual(
            response.data['followings'][1]['user']['username'],
            'zhuzhu_following1',
        )
        self.assertEqual(
            response.data['followings'][2]['user']['username'],
            'zhuzhu_following0',
        )

    def test_followers(self):
        url = FOLLOWERS_URL.format(self.zhuzhu.id)
        # 1. post is not allowed
        response = self.anonymous_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 2. get is ok
        response = self.anonymous_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['followers']), 2)
        # 3. 确保按照时间倒序
        ts0 = response.data['followers'][0]['created_at']
        ts1 = response.data['followers'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(
            response.data['followers'][0]['user']['username'],
            'zhuzhu_follower1',
        )
        self.assertEqual(
            response.data['followers'][1]['user']['username'],
            'zhuzhu_follower0',
        )