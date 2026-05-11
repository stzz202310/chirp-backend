from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from accounts.models import UserProfile
from testing.testcases import TestCase

LOGIN_URL = '/api/accounts/login/'
LOGOUT_URL = '/api/accounts/logout/'
SIGNUP_URL = '/api/accounts/signup/'
LOGIN_STATUS_URL = '/api/accounts/login_status/'
USER_PROFILE_DETAIL_URL = '/api/profiles/{}/'


class AccountApiTests(TestCase):

    def setUp(self):
        super(AccountApiTests, self).setUp()
        self.client = APIClient()
        self.user = self.create_user(
            username='tester',
            password='correct password',
            email='tester@example.com',
        )

    def test_login(self):
        # 1. 测试必须用 POST 而不是 GET
        data = {'username': self.user.username, 'password': 'correct password'}
        response = self.client.get(path=LOGIN_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 2. 用了 POST 但是密码错误 | 用户不存在
        data = {'username': self.user.username, 'password': 'wrong password'}
        response = self.client.post(path=LOGIN_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], "Username and password does not match.")

        data = {'username': 'wrong username', 'password': 'correct password'}
        response = self.client.post(LOGIN_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['errors']['username'][0], "User does not exist.")

        # 3. 验证还没有登陆
        response = self.client.get(path=LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

        # 4. 登陆成功
        data = {'username': self.user.username, 'password': 'correct password'}
        response = self.client.post(path=LOGIN_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEqual(response.data['user'], None)
        self.assertEqual(response.data['user']['id'], self.user.id)

        # 5. 验证已经登录了
        response = self.client.get(path=LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

    def test_logout(self):
        # 1 先登陆, 验证用户已经等登陆
        data = {'username': self.user.username, 'password': 'correct password'}
        response = self.client.post(path=LOGIN_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(path=LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

        # 2. 登出必须用 POST
        response = self.client.get(path=LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.post(path=LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 3 验证用户已经登出
        response = self.client.get(path=LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

    def test_signup(self):
        data = {
            'username': 'new tester',
            'password': 'new tester',
            'email': 'newtester@example.com',
        }
        # 1 注册必须用 POST
        response = self.client.get(path=SIGNUP_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 2 测试错误的邮箱
        response = self.client.post(path=SIGNUP_URL,data={
            'username': 'new tester',
            'password': 'new tester',
            'email': 'not a correct email',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 3 测试密码 太短
        response = self.client.post(path=SIGNUP_URL, data={
            'username': 'new tester',
            'password': '123',
            'email': 'newtester@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 4 测试用户名 太长
        response = self.client.post(path=SIGNUP_URL, data={
            'username': 'username is very very very very very long',
            'password': 'new tester',
            'email': 'newtester@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 5 成功注册
        response = self.client.post(path=SIGNUP_URL,data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['user']['username'], 'new tester')

        # 6. 验证 user profile 已经被创建
        created_user_id = response.data['user']['id']
        profile = UserProfile.objects.filter(user_id=created_user_id).first()
        self.assertNotEqual(profile, None)

        # 7. 验证用户已经登入
        response = self.client.get(path=LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)


class UserProfileAPITests(TestCase):

    def test_update(self):
        taotao, taotao_client = self.create_user_and_client(username='taotao')
        zhuzhu, zhuzhu_client = self.create_user_and_client(username='zhuzhu')
        profile_taotao = taotao.profile
        profile_taotao.nickname = 'old nickname'
        profile_taotao.save()
        url = USER_PROFILE_DETAIL_URL.format(profile_taotao.id)

        # 0. use wrong profile_id
        url_wrong = USER_PROFILE_DETAIL_URL.format(profile_taotao.id + 1)
        response = taotao_client.put(path=url_wrong, data={'nickname': 'new nickname'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        profile_taotao.refresh_from_db()
        self.assertEqual(profile_taotao.nickname, 'old nickname')

        # 0. anonymous user can not update profile
        response = self.anonymous_client.put(path=url, data={'nickname': 'new nickname'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # print(response.data)
        # {'detail': ErrorDetail(string='Authentication ...', code='not_authenticated')}
        self.assertEqual(response.data['detail'], 'Authentication credentials were not provided.')
        profile_taotao.refresh_from_db()
        self.assertEqual(profile_taotao.nickname, 'old nickname')

        # 1. profile can only be updated by owner
        response = zhuzhu_client.put(path=url, data={'nickname': 'new nickname'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # {'detail': ErrorDetail(string='You do not ...', code='permission_denied')}
        self.assertEqual(response.data['detail'], 'You do not have permission to access this object.')
        profile_taotao.refresh_from_db()
        self.assertEqual(profile_taotao.nickname, 'old nickname')

        # 2. update nickname
        response = taotao_client.put(path=url, data={'nickname': 'new nickname'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile_taotao.refresh_from_db()
        self.assertEqual(profile_taotao.nickname, 'new nickname')

        # 3. update avatar
        data = {'avatar': SimpleUploadedFile(
            name='my-avatar.jpg',
            content=str.encode('a fake image'), # bytes 字节类型
            content_type='image/jpeg',
        )}
        response = taotao_client.put(path=url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # 为什么不是断言 ('my-avatar.jpg' in response.data['avatar'])
        # Django 在保存 FileField 时, 如果文件名已存在，会自动重命名以避免覆盖
        # 例如: my-avatar.jpg, my-avatar_3v4R8U4.jpg
        self.assertEqual('my-avatar' in response.data['avatar'], True)
        profile_taotao.refresh_from_db()
        self.assertIsNotNone(profile_taotao.avatar)