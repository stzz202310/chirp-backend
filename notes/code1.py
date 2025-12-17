from django.db import models
from django.db.models import F
from django.db.models.signals import post_save, pre_delete
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core import serializers
from django.core.cache import caches
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.serializers.json import DjangoJSONEncoder
from django.test import TestCase
from django.urls import include, path
from django.utils import timezone
from django.utils.decorators import method_decorator

from rest_framework import routers
from rest_framework import serializers
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny, BasePermission, IsAdminUser
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import exception_handler as drf_exception_handler

from notifications.models import Notification
from notifications.signals import notify

from celery import Celery
from celery import shared_task
from kombu import Queue

from ratelimit.decorators import ratelimit
from ratelimit.exceptions import Ratelimited

from dateutil import parser
from datetime import datetime
import pytz

"""
Model / ViewSet / Serializer: 尽量少继承，提升代码的可读性

| Serializer 类型     | 是否必须写 `Meta.model` | 特点 / 原因                           |
| ----------------- | ---------------------- | -------------------------------------|
| `ModelSerializer` | ✅ 必须写               | 绑定 Model，自动生成字段和校验，
                                               提供默认 `create()` 和 `update()` 方法
                                               `serializer.save()` 会直接操作数据库 {via creat() OR update()}
                                               
| `Serializer`      | ❌ 不需要写             | 不绑定 Model
                                               需要手动定义字段和 `create()` / `update()` 方法
                                               `serializer.save()` 是否可用取决于是否自定义了 `create()` |

================================================================================================================

ModelViewSet：[尽量不要用] 使用简单，但容易不小心暴露不必要的接口 (自动暴露所有 CRUD)
GenericViewSet：需要手动实现，但更安全、更灵活，推荐在涉及用户账户或敏感数据的接口使用 [白名单: 需要什么加什么]
关联模型: 通过`queryset`[def get_queryset(self):] 和`serializer_class`[def get_permissions(self):]

| 特性          | `ModelViewSet`                               | `GenericViewSet`                 |
| ------------ | -------------------------------------------- | -------------------------------- |
| 自动生成 CRUD | ✅（list, create, retrieve, update, destroy） | ❌ 需要自己手动实现方法             |
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

调用 django_authenticate {检查用户名密码是否正确} + django_login {将 user 信息写入 request.session} 后:
request.user = 已登录的 User 对象
request.session 中保存了登录状态
request.user.is_authenticated = True

=======================================================================================

django_logout(request)

user = django_authenticate([request], username=username, password=password)
1. 接收 request（可选）和用户名/密码
2. 查找数据库中的用户记录
3. 对比用户密码（Django 存的是哈希值，进行哈希验证）
4. 如果用户名和密码匹配 → 返回一个 user 对象
   如果不匹配 → 返回 None
   if not user or user.is_anonymous:

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

不同的需求，用不同的 Serializer —— 更安全、隔离、解耦
GET /api/tweets/1/?format=with_comments
GET /api/tweets/1/?format=mini
GET /api/tweets/1/?format=full
GET /api/tweets/1/?format=admin

tweets.api.views
def get_serializer_class(self):
    format = self.request.get_params.get('_format') OR get('format')
    if format == 'with_comments': return TweetSerializerWithComment
	if format == 'mini':          return TweetSerializerMini
	...
	return TweetSerializer

def list():
    serializer_class = self.get_serializer_class()
    serializer = serializer_class(data=request.data)

=======================================================================================

class Serializer(serializers.ModelSerializer):
    user = UserSerializerForComment()
    user = UserSerializerForFriendship(source='from_user')          # instance = friendship.from_user
    comments = CommentSerializer(source='comment_set', many=True)   # queryset = tweet.comment_set

    class Meta: model = User    fields = ('user', 'comments',)      # 白名单 返回给前端 | 展示部分信息

    def __init__(self, instance=None, data=empty, **kwargs):
    
    # views.py 
    #   serializer.is_valid():  调用 validate
    #   serializer.save():      调用 create() without instance | update() with instance
        
    def validate(self, attrs):  return attrs [validated data: 验证+处理后的输入数据，也可以是未处理的原数据]
    def create(self, validated_data):           return instance
    def update(self, instance, validated_data): return instance [修改后的 instance]


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
    serializer.errors       # You must call .is_valid() before accessing .errors
    serializer.validated_data
    serializer.save()       # create() or update(): return instance
    
    views.py        serializer = TweetSerializerForCreate(data=request.data, context={'request': request},)
    serializers.py  def create(self, validated_data): user = self.context['request'].user
    OR
    data = {'user_id': request.user.id,
            'tweet_id': request.data.get('tweet_id'),
            'content': request.data.get('content'),}
    serializer = CommentSerializerForCreate(data=data)


3 初始化时最好显式写出 instance= 或 data=，避免 DRF 把参数搞反, 推荐写法
    def __init__(self, instance=None, data=empty, **kwargs):
    serializer = LoginSerializer(data=request.data)
    serializer = LoginSerializer(instance=user)


4. def create(self, validated_data): return instance
    self = 当前 Serializer 实例
    validated_data = self.validated_data, create(validated_data) 传参数是为了
        a. 与 def update(self, instance, validated_data) 接口一致
        b. 保持 create() 接口独立，可测试，不依赖 Serializer 的状态


username = serializer.validated_data.get('username') ==> Login
username = request.data.get('username')           # ❌原始请求数据, 未校验
username = serializer.validated_data['username']  # ✅serializer 校验后的数据; 会抛 KeyError

=======================================================================================

serializer.is_valid() DRF 会依次执行 三个步骤:
步骤 1：字段级验证 (Field-level validation)     username = serializers.CharField(min_length=6, max_length=20)
步骤 2：自定义字段级验证方法 (Optional)  serializers.py: def validate_<fieldname>(self, data):
步骤 3：全局验证 validate(self, data)  serializers.py: def validate(self, data): 会覆盖父类的全局 validate 方法

instance.save() → SQL INSERT/UPDATE 时检查 Django model {models.py}
1. content = models.TextField(max_length=140)
2. unique_together

=======================================================================================

ModelSerializer 默认实现了 create() 和 update() 方法，大致逻辑是:

def update(self, instance, validated_data):
    for attr, value in validated_data.items():
        setattr(instance, attr, value)
    instance.save()
    return instance

def create(self, validated_data):
    # 1. 模型的管理器（通常是 objects）
    ModelClass = self.Meta.model

    # 2. 使用模型的默认管理器创建实例
    instance = ModelClass.objects.create(**validated_data)

    return instance

================================================================================================================

------------------------- models.py ------------------------
@property
def XXX(self):
def like_set(self):

def __str__(self):
------------------------------------------------------------


------------------------ api.views -------------------------
def get_permissions(self):
def get_queryset(self):

def list(self, request, *args, **kwargs):
def retrieve(self, request, *args, **kwargs):
def create(self, request, *args, **kwargs):
def update(self, request, *args, **kwargs):
def destroy(self, request, *args, **kwargs):

@action(methods=['GET'], detail=False, url_path='unread-count')
def unread_count(self, request, *args, **kwargs):
@action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
def follow(self, request, pk):
------------------------------------------------------------


--------------------- api.serializers ----------------------
def validate(self, data):
def create(self, validated_data):
def update(self, instance, validated_data):

def get_or_create(self):
def cancel(self):

likes_count = serializers.SerializerMethodField()
def get_likes_count(self, obj):
------------------------------------------------------------

"""