from rest_framework import status
from rest_framework.test import APIClient

from friendships.services import FriendshipService
from testing.testcases import TestCase
from utils.paginations import EndlessPagination

FOLLOW_URL = '/api/friendships/{}/follow/'
UNFOLLOW_URL = '/api/friendships/{}/unfollow/'
FOLLOWERS_URL = '/api/friendships/{}/followers/'
FOLLOWINGS_URL = '/api/friendships/{}/followings/'


class FriendshipApiTests(TestCase):

    def setUp(self):
        super(FriendshipApiTests, self).setUp()
        self.taotao = self.create_user('taotao')
        self.taotao_client = APIClient()
        self.taotao_client.force_authenticate(self.taotao)

        self.zhuzhu=self.create_user('zhuzhu')
        self.zhuzhu_client = APIClient()
        self.zhuzhu_client.force_authenticate(self.zhuzhu)

        # create followings and followers for zhuzhu
        for i in range(2):
            follower = self.create_user(f'zhuzhu_follower{i}')
            self.create_friendship(from_user=follower, to_user=self.zhuzhu)
        for i in range(3):
            following = self.create_user(f'zhuzhu_following{i}')
            self.create_friendship(from_user=self.zhuzhu, to_user=following)

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

        # 5. 重复 follow 静默处理
        response = self.zhuzhu_client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['duplicate'], True)

        # 6. 反向关注会创建新的数据
        before_count = FriendshipService.get_following_count(from_user_id=self.taotao.id)
        url = FOLLOW_URL.format(self.zhuzhu.id)
        response = self.taotao_client.post(path=url)
        after_count = FriendshipService.get_following_count(from_user_id=self.taotao.id)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(after_count, before_count + 1)

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
        self.create_friendship(from_user=self.zhuzhu, to_user=self.taotao)
        before_count = FriendshipService.get_following_count(from_user_id=self.zhuzhu.id)
        response = self.zhuzhu_client.post(path=url)
        after_count = FriendshipService.get_following_count(from_user_id=self.zhuzhu.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 1)
        self.assertEqual(after_count, before_count - 1)

        # 5. 没有 follow 的情况下 unfollow 静默处理
        before_count = FriendshipService.get_following_count(from_user_id=self.zhuzhu.id)
        response = self.zhuzhu_client.post(url)
        after_count = FriendshipService.get_following_count(from_user_id=self.zhuzhu.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 0)
        self.assertEqual(after_count, before_count)

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
        self.assertEqual(len(response.data['results']), 3)

        # 3. 确保按照时间倒序
        ts0 = response.data['results'][0]['created_at']
        ts1 = response.data['results'][1]['created_at']
        ts2 = response.data['results'][2]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(ts1 > ts2, True)
        self.assertEqual(
            response.data['results'][0]['user']['username'],
            'zhuzhu_following2',
        )
        self.assertEqual(
            response.data['results'][1]['user']['username'],
            'zhuzhu_following1',
        )
        self.assertEqual(
            response.data['results'][2]['user']['username'],
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
        self.assertEqual(len(response.data['results']), 2)

        # 3. 确保按照时间倒序
        ts0 = response.data['results'][0]['created_at']
        ts1 = response.data['results'][1]['created_at']
        self.assertEqual(ts0 > ts1, True)
        self.assertEqual(
            response.data['results'][0]['user']['username'],
            'zhuzhu_follower1',
        )
        self.assertEqual(
            response.data['results'][1]['user']['username'],
            'zhuzhu_follower0',
        )

    def test_followers_pagination(self):
        page_size = EndlessPagination.page_size
        friendships = []
        for i in range(page_size * 2):
            follower = self.create_user(username=f'taotao_follower{i}')
            friendship = self.create_friendship(from_user=follower, to_user=self.taotao)
            friendships.append(friendship)
            if follower.id % 2 == 0:
                self.create_friendship(from_user=self.zhuzhu, to_user=follower)

        url = FOLLOWERS_URL.format(self.taotao.id)
        self._paginate_until_the_end(url=url, expect_pages=2, friendships=friendships)

        # anonymous hasn't followed any users
        response = self.anonymous_client.get(path=url)
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)

        # zhuzhu has followed users with even id
        response = self.zhuzhu_client.get(path=url)
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)

    def test_followings_pagination(self):
        page_size = EndlessPagination.page_size
        friendships = []
        for i in range(page_size * 2):
            following = self.create_user(username=f'taotao_following{i}')
            friendship = self.create_friendship(from_user=self.taotao, to_user=following)
            friendships.append(friendship)
            if following.id % 2 == 0:
                self.create_friendship(from_user=self.zhuzhu, to_user=following)

        url = FOLLOWINGS_URL.format(self.taotao.id)
        self._paginate_until_the_end(url=url, expect_pages=2, friendships=friendships)

        # anonymous hasn't followed any users
        response = self.anonymous_client.get(path=url)
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], False)

        # zhuzhu has followed users with even id
        response = self.zhuzhu_client.get(path=url)
        for result in response.data['results']:
            has_followed = (result['user']['id'] % 2 == 0)
            self.assertEqual(result['has_followed'], has_followed)

        # taotao has followed all his following users
        response = self.taotao_client.get(path=url)
        for result in response.data['results']:
            self.assertEqual(result['has_followed'], True)

        # test pull new friendships
        last_created_at = friendships[-1].created_at
        response = self.taotao_client.get(path=url, data={'created_at__gt': last_created_at})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

        new_friends = [self.create_user(username=f'big_v{i}') for i in range(3)]
        new_friendships = []
        for new_friend in new_friends:
            new_friendships.append(self.create_friendship(from_user=self.taotao, to_user=new_friend))
        response = self.taotao_client.get(path=url, data={'created_at__gt': last_created_at})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
        for result, friendship in zip(response.data['results'], reversed(new_friendships)):
            self.assertEqual(result['created_at'], friendship.created_at)
            self.assertEqual(result['user']['id'], friendship.to_user_id)

    def _paginate_until_the_end(self, url, expect_pages, friendships):
        results, pages = [], 0
        response = self.anonymous_client.get(path=url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results.extend(response.data['results'])
        pages += 1

        while response.data['has_next_page']:
            last_item = response.data['results'][-1]
            response = self.anonymous_client.get(
                path=url,
                data={'created_at__lt': last_item['created_at']}
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results.extend(response.data['results'])
            pages += 1

        self.assertEqual(len(results), len(friendships))
        self.assertEqual(pages, expect_pages)

        # friendship is in ascending order, results is in descending order
        for result, friendship in zip(results, friendships[::-1]):
            self.assertEqual(result['created_at'], friendship.created_at)

    def _test_friendship_pagination(self, url, page_size, max_page_size):
        # ⚠️ legacy function
        response = self.anonymous_client.get(path=url, data={'page': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)

        response = self.anonymous_client.get(path=url, data={'page': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 2)
        self.assertEqual(response.data['has_next_page'], False)

        response = self.anonymous_client.get(path=url, data={'page': 3})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # test user can not customize page_size exceeds max_page_size
        response = self.anonymous_client.get(
            path=url,
            data={'page': 1, 'size': max_page_size + 1,},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), max_page_size)
        self.assertEqual(response.data['total_pages'], 2)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)

        # test user can customize page size by param size
        response = self.anonymous_client.get(path=url, data={'page': 1, 'size': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['total_pages'], page_size)
        self.assertEqual(response.data['total_results'], page_size * 2)
        self.assertEqual(response.data['page_number'], 1)
        self.assertEqual(response.data['has_next_page'], True)