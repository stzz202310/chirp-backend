from django.db import models
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.test import TestCase
from django.urls import include, path

from rest_framework import exceptions
from rest_framework import routers
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.test import APIClient

"""
| Serializer 类型     | 是否必须写 `Meta.model` | 特点 / 原因                           |
| ----------------- | ---------------------- | -------------------------------------|
| `ModelSerializer` | ✅ 必须写               | 绑定 Model，自动生成字段和校验，
                                               提供默认 `create()` 和 `update()` 方法
                                               `serializer.save()` 会直接操作数据库 {via creat() OR update()}
                                               
| `Serializer`      | ❌ 不需要写             | 不绑定 Model
                                               需要手动定义字段和 `create()` / `update()` 方法
                                               `serializer.save()` 是否可用取决于是否自定义了 `create()` |

ModelViewSet：[尽量不要用] 方便但暴露多(自动暴露所有 CRUD)，容易出现安全漏洞
ViewSet：需要手动实现，但更安全、更灵活，推荐在涉及用户账户或敏感数据的接口使用

| 特性          | `ModelViewSet`                               | `ViewSet`           |
| ------------ | -------------------------------------------- | ------------------- |
| 自动生成 CRUD | ✅（list, create, retrieve, update, destroy） | ❌ 需要自己手动实现方法             |
| 自动关联模型   | ✅ 通过`queryset`和`serializer_class`[⚠️必须]  | ❌ 没有自动绑定模型，需要自己处理数据 |
| 灵活性        | 较低（自动暴露所有 CRUD）                        | 高（只暴露你想实现的接口）           |

================================================================================================================

request = {
    "是谁发来的？"         → request.user
    "带来了什么数据？"      → request.data
    "URL 参数是什么？"     → request.query_params
    "是否登录？"           → request.user.is_authenticated
}

POST:   request.data            参数位置: 请求体(HTTP Body)中, 而不是URL
GET:    request.query_params    参数位置: URL末尾的问号之后

在请求 login 前
request.user = AnonymousUser
request.data = 客户端发送的用户名和密码（未校验）
request.user.is_authenticated = False

调用 django_authenticate {检查用户名密码是否正确} + login {将 user 信息写入 request.session} 后:
request.user = 已登录的 User 对象
request.session 中保存了登录状态
request.user.is_authenticated = True

================================================================================================================

django_login(request, user)
django_logout(request)
user = django_authenticate([request], username=username, password=password)
if not user or user.is_anonymous:
1. 接收 request（可选）和用户名/密码
2. 查找数据库中的用户记录
3. 对比用户密码（Django 存的是哈希值，进行哈希验证）
4. 如果用户名和密码匹配 → 返回一个 user 对象
   如果不匹配 → 返回 None

django_login(request, user)
1. 从 request 获取或创建 request.session
2. 在 session 中写入用户 id（通常是 request.session['_auth_user_id'] = user.id）
3. 设置 request.user = user，方便当前请求访问
4. 更新最后登录时间等用户状态（可选）
5. 生成一个 sessionid cookie，放到 response 中返回给客户端

服务器内部：Session table 里增加/更新一行数据，例如：
| session_id | session_data    | expire_date |
| ---------- | --------------- | ----------- |
| abc123     | {"user_id": 42} | 2025-11-10  |

response（服务器返回给客户端）
HTTP response 头部会设置 Set-Cookie: sessionid=abc123
浏览器收到后保存 cookie，后续每次请求会自动带上这个 cookie

================================================================================================================

return Response(data=data, status=status.HTTP_200_OK)
return Response(data={'tweets': serializer.data}) ==> dict {'tweets':JSON}

response = self.client.get(LOGIN_STATUS_URL)
self.assertEqual(response.data['has_logged_in'], False)

================================================================================================================

class Serializer(serializers.ModelSerializer):
    class Meta: model = User    fields = ('username', 'email',)

    def __init__(self, instance=None, data=empty, **kwargs):    
    def validate(self, attrs): return attrs     # will be called when .is_valid() is called
    def create(self, validated_data): return instance

1 序列化（将对象 -> JSON/字典）
    serializer = LoginSerializer(instance=user)
    serializer.data  # 得到序列化后的字典
    
    1. if tweets 是一个 QuerySet
    2. if tweets 是一个模型对象列表 (如[tweet1, tweet2, tweet3])
    serializer = TweetSerializer(instance=tweets, many=True)
    # 一般来说 json 格式的 response 默认都要用 hash 的格式
    # 而不能用 list 的格式（约定俗成）
    return Response(data={'tweets': serializer.data})


2 反序列化（验证客户端数据 -> Python 对象）
    serializer = LoginSerializer(data=request.data)
    serializer.is_valid()   # 调用验证逻辑
    serializer.errors
    serializer.validated_data
    serializer.save()       # create() or update()
    
    serializer = TweetSerializerForCreate(data=request.data, context={'request': request},)
    serializers.py|def create(self, validated_data): user = self.context['request'].user


3 初始化时最好显式写出 instance= 或 data=，避免 DRF 把参数搞反, 推荐写法
    def __init__(self, instance=None, data=empty, **kwargs):
    serializer = LoginSerializer(data=request.data)
    serializer = LoginSerializer(instance=user)


4. def create(self, validated_data): return instance
    self = 当前 Serializer 实例
    validated_data = self.validated_data, create(validated_data) 传参数是为了
        a. 与 update(instance, validated_data) 接口一致
        b. 保持 create() 接口独立，可测试，不依赖 Serializer 的状态


serializer = LoginSerializer(data=request.data)
serializer.is_valid()
serializer.errors   # You must call .is_valid() before accessing .errors
user = serializer.save() ==> Signup

username = serializer.validated_data.get('username') ==> Login
username = request.data.get('username')           # ❌原始请求数据, 未校验
username = serializer.validated_data['username']  # ✅serializer 校验后的数据; 会抛 KeyError
password = serializer.validated_data.get('password')

"""
