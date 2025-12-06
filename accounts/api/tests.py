from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient  # 用于在测试中发送 API 请求

from accounts.models import UserProfile
from testing.testcases import TestCase

LOGIN_URL = '/api/accounts/login/'  # 注意末尾斜杠 '/' 否则 自动重定向，status_code = 301
LOGOUT_URL = '/api/accounts/logout/'
SIGNUP_URL = '/api/accounts/signup/'
LOGIN_STATUS_URL = '/api/accounts/login_status/'
USER_PROFILE_DETAIL_URL = '/api/profiles/{}/'


class AccountApiTests(TestCase):

    def setUp(self):
        self.clear_cache()
        # 这个函数会在每个 test function 执行的时候被执行
        self.client = APIClient()   # 类似 手动测试时的浏览器
        self.user = self.create_user(
            username='tester',
            password='correct password',
            email='tester@example.com',
        )
        # self.user.password 哈希加密后的密码

    def test_login(self):
        # 每个测试函数必须以 test_ 开头，才会被自动调用 进行测试
        # 1. 测试必须用 POST 而不是 GET
        response = self.client.get(LOGIN_URL, data={
            'username': self.user.username,
            'password': 'correct password',
        })  # GET+参数 → 放在 URL 中: /api/account/login/?username=XXX&password=XXX
        # 登陆失败, http status code 返回 405 = METHOD_NOT_ALLOWED
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 2. 用了 POST 但是密码错误 | 用户不存在
        response = self.client.post(LOGIN_URL, data={
            'username': self.user.username,
            'password': 'wrong password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(LOGIN_URL, data={
            'username': 'wrong username',
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['errors']['username'][0], "User does not exist.")

        # 3. 验证还没有登陆
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

        # 4. 登陆成功
        response = self.client.post(LOGIN_URL, data={
            'username': self.user.username,
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotEquals(response.data['user'], None)
        self.assertEqual(response.data['user']['id'], self.user.id)

        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

    def test_logout(self):
        # 1 先登陆, 验证用户已经等登陆
        response = self.client.post(LOGIN_URL, data={
            'username': self.user.username,
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

        # 2. 登出必须用 POST
        response = self.client.get(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 3 验证用户已经登出
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

    def test_signup(self):
        data = {
            'username': 'new tester',
            'password': 'new tester',
            'email': 'newtester@example.com',
        }
        # 1 注册必须用 POST
        response = self.client.get(SIGNUP_URL, data=data)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 2 测试错误的邮箱
        response = self.client.post(SIGNUP_URL,data={
            'username': 'new tester',
            'password': 'new tester',
            'email': 'not a correct email',
        })
        # print(response.data)      解析前, 原始响应内容 (bytes) 400错误
        # print(response.content)   解析后，Python 对象 (dict)  500错误
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 3 测试密码 太短
        response = self.client.post(SIGNUP_URL,{
            'username': 'new tester',
            'password': '123',
            'email': 'newtester@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 4 测试用户名 太长
        response = self.client.post(SIGNUP_URL,{
            'username': 'username is very very very very very long',
            'password': 'new tester',
            'email': 'newtester@example.com',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 5 成功注册
        response = self.client.post(SIGNUP_URL,data=data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['user']['username'], 'new tester')

        # 6. 验证 user profile 已经被创建
        created_user_id = response.data['user']['id']
        profile = UserProfile.objects.filter(user_id=created_user_id).first()
        self.assertNotEqual(profile, None)

        # 7. 验证用户已经登入
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)


class UserProfileAPITests(TestCase):

    def test_update(self):
        taotao, taotao_client = self.create_user_and_client(username='taotao')
        zhuzhu, zhuzhu_client = self.create_user_and_client(username='zhuzhu')
        profile_taotao = taotao.profile
        profile_taotao.nickname = 'old nickname'
        profile_taotao.save()
        url = USER_PROFILE_DETAIL_URL.format(profile_taotao.id)

        # 0. user wrong profile_id
        url_wrong = USER_PROFILE_DETAIL_URL.format(1000)
        response = taotao_client.put(path=url_wrong, data={'nickname': 'new nickname'})
        # 返回 404
        # a. twitter.urls 如果没有添加 router.register()
        # b. path='/api/profile/{}/' [profiles vs profile]
        # c. detail=True: self.get_object()
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        profile_taotao.refresh_from_db()
        self.assertEqual(profile_taotao.nickname, 'old nickname')


        # 1. anonymous user can not update profile
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
        # 为什么不是 ('my-avatar.jpg' in ...)
        # django: 文件名如果已经存在 my-avatar_3v4R8U4.jpg
        self.assertEqual('my-avatar' in response.data['avatar'], True)
        profile_taotao.refresh_from_db()
        self.assertIsNotNone(profile_taotao.avatar)