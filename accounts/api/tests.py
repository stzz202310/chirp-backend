from django.test import TestCase
from rest_framework.test import APIClient   # 用于在测试中发送 API 请求
from django.contrib.auth.models import User


LOGIN_URL = '/api/accounts/login/'  # 注意末尾斜杠 '/' 否则 自动重定向，status_code = 301
LOGOUT_URL = '/api/accounts/logout/'
SIGNUP_URL = '/api/accounts/signup/'
LOGIN_STATUS_URL = '/api/accounts/login_status/'


class AccountApiTests(TestCase):

    def setUp(self):
        # 这个函数会在每个 test function 执行的时候被执行
        self.client = APIClient()   # 类似 手动测试时的浏览器
        self.user = self.create_user(
            username='tester',
            password='correct password',
            email='tester@example.com',
        )
        # self.user.password 哈希加密后的密码

    def create_user(self, username, password, email):
        return User.objects.create_user(username=username, password=password, email=email)

    def test_login(self):
        # 每个测试函数必须以 test_ 开头，才会被自动调用 进行测试
        # 1. 测试必须用 POST 而不是 GET
        response = self.client.get(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })  # GET+参数 → 放在 URL 中: /api/account/login/?username=XXX&password=XXX
        # 登陆失败, http status code 返回 405 = METHOD_NOT_ALLOWED
        self.assertEqual(response.status_code, 405)

        # 2. 用了 POST 但是密码错误 | 用户不存在
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'wrong password',
        })
        self.assertEqual(response.status_code, 400)

        response = self.client.post(LOGIN_URL, {
            'username': 'wrong username',
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['errors']['username'][0], "User does not exist.")

        # 3. 验证还没有登陆
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], False)

        # 4. 登陆成功
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotEquals(response.data['user'], None)
        self.assertEqual(response.data['user']['email'], self.user.email)

        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

    def test_logout(self):
        # 1 先登陆, 验证用户已经等登陆
        response = self.client.post(LOGIN_URL, {
            'username': self.user.username,
            'password': 'correct password',
        })
        self.assertEqual(response.status_code, 200)
        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)

        # 2. 登出必须用 POST
        response = self.client.get(LOGOUT_URL)
        self.assertEqual(response.status_code, 405)

        response = self.client.post(LOGOUT_URL)
        self.assertEqual(response.status_code, 200)

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
        response = self.client.get(SIGNUP_URL, data)
        self.assertEqual(response.status_code, 405)

        # 2 测试错误的邮箱
        response = self.client.post(SIGNUP_URL,{
            'username': 'new tester',
            'password': 'new tester',
            'email': 'not a correct email',
        })
        # print(response.data)      解析前, 原始响应内容 (bytes) 400错误
        # print(response.content)   解析后，Python 对象 (dict)  500错误
        self.assertEqual(response.status_code, 400)

        # 3 测试密码 太短
        response = self.client.post(SIGNUP_URL,{
            'username': 'new tester',
            'password': '123',
            'email': 'newtester@example.com',
        })
        self.assertEqual(response.status_code, 400)

        # 4 测试用户名 太长
        response = self.client.post(SIGNUP_URL,{
            'username': 'username is very very very very very long',
            'password': 'new tester',
            'email': 'newtester@example.com',
        })
        self.assertEqual(response.status_code, 400)

        # 5 成功注册
        response = self.client.post(SIGNUP_URL,data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['success'], True)
        self.assertEqual(response.data['user']['username'], 'new tester')

        response = self.client.get(LOGIN_STATUS_URL)
        self.assertEqual(response.data['has_logged_in'], True)
