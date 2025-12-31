from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.test import TestCase as DjangoTestCase
from rest_framework.test import APIClient

from comments.models import Comment
from django_hbase.models import HBaseModel
from friendships.services import FriendshipService
from gatekeeper.models import Gatekeeper
from likes.models import Like
from newsfeeds.models import NewsFeed
from tweets.models import Tweet
from utils.redis_client import RedisClient

"""
create {comment, tweet, like, newsfeed}
1. 前端要求创建 via API
2. 测试要求创建 via testcases.create_tweet(user=user)
"""
class TestCase(DjangoTestCase):
    """""""""
    transaction 事务 是数据库层面的概念
    | 特性         | 含义    |
    | ----------- | ------- |
    | Atomicity   | 原子性   | 要么全做，要么全不做
    | Consistency | 一致性   |
    | Isolation   | 隔离性   |
    | Durability  | 持久性   |

    1. 最原始的事务写法 (SQL)
    BEGIN;
    INSERT INTO tweet ...;
    INSERT INTO timeline ...;
    COMMIT;     如果没异常
    ROLLBACK;   如果抛异常
    
    2. Django 中的 transaction API
    from django.db import transaction
    transaction.commit()
    transaction.rollback()
    with transaction.atomic():
        # BEGIN
        do_something()
        # COMMIT or ROLLBACK [抛异常 → 自动 rollback]

    3. python manage.py test
    │
    ├─ CREATE DATABASE test_twitter; 创建 test_twitter 数据库
    │
    ├─ 运行 test case (TestCase)
    │   ├─ BEGIN
    │   ├─ test_xxx
    │   └─ ROLLBACK     不论测试方法正常结束，还是抛异常，最后都会执行 ROLLBACK
    │
    └─ DROP DATABASE test_twitter; ← 测试结束
    
    TestCase: 在每个测试方法外面包了一层 transaction.atomic()
    TestCase 的 atomic 行为是: ❌不允许 commit  ✅只用来隔离测试
    测试正常通过                      测试失败|抛异常
    BEGIN                           BEGIN
        INSERT user                     INSERT user
        ASSERT OK                       AssertionError
    ROLLBACK    数据回滚             ROLLBACK      数据同样回滚
    """

    hbase_tables_created = False

    def setUp(self):
        self.clear_cache()
        try:
            self.hbase_tables_created = True
            # __subclasses__(): 用来查看某个类的"直接子类"
            # class A: pass
            # class B(A): pass
            # class C(B): pass      C 不是 A 的直接子类
            # A.__subclasses__()    [<class '__main__.B'>]
            for hbase_model_class in HBaseModel.__subclasses__():
                hbase_model_class.create_table()
        except Exception:
            self.tearDown()
            raise
        # except Exception as e:
        #   raise e

    def tearDown(self):
        if not self.hbase_tables_created:
            return
        for hbase_model_class in HBaseModel.__subclasses__():
            hbase_model_class.drop_table()

    """
    情况 1
    class TestAPI(TestCase):
        pass
    
    DjangoTestCase.setUp()
    └─ TestCase.setUp()
    
    tearDown(): 不论测试通过, 失败(assert 失败), 还是抛异常, 都会执行 TestCase.tearDown()
    try:
        self._pre_setup()     # Django 内部
        self.setUp()          # TestCase.setUp
        self.test_xxx()
    finally:
        self.tearDown()       # TestCase.tearDown  ← 一定执行
        self._post_teardown() # Django 内部（rollback）
    ====================================================================
    情况 2
    class TestAPI(TestCase):
        def setUp(self):
            do_something()
    
    DjangoTestCase.setUp()
    └─ TestAPI.setUp()
    ====================================================================
    情况 3
    class TestAPI(TestCase):
        def setUp(self):
            super().setUp() # 👈 关键
            do_something_else()
            
    DjangoTestCase.setUp()
    └─ TestCase.setUp()
       └─ TestAPI.setUp()
    """

    def clear_cache(self):
        caches['testing'].clear()
        RedisClient.clear()
        # Gatekeeper.set_kv(gk_name='switch_friendship_to_hbase', key='percent', value=100)

    @property
    def anonymous_client(self):
        # return APIClient() 每次调用 anonymous_client 都会创建一个新的实例
        # 在当前测试用例实例上缓存一个 _anonymous_client, 实现 APIClient 单例复用
        # 类似地，QuerySet 在 Django 内部也有 instance 级别的缓存机制
        if hasattr(self, '_anonymous_client'):
            # hasattr(obj, key)
            # getattr(obj, key, default=None)
            # setattr(obj, key, value)
            # ⚠️ key 必须是字符串 (str)
            # ⚠️ value 几乎没有类型限制 (int, str, list, dict, None, 自定义对象)
            return self._anonymous_client
        self._anonymous_client = APIClient()
        return self._anonymous_client

    def create_user(self, username, email=None, password=None):
        if password is None:
            password = 'generic password'
        if email is None:
            email = f'{username}@zhuzhu.com'
        # 不能写成 User.objects.create()
        # 因为 password 需要被加密, username 和 email 需要进行一些 normalize 处理
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

    def create_user_and_client(self, *args, **kwargs):
        # * 展开 list
        # a = [1, 2], b = [3, 4]
        # c = [a, b]        c = [[1, 2], [3, 4]]
        # c = [*a, * b]     c = [1, 2, 3, 4]        展开

        # ** 展开 dict
        # a = {'x': 1}, b = {'y': 2}
        # c = [a, b]        c = [{'x': 1}, {'y': 2}]
        # c = {*a, *b}      c = {'x', 'y'}
        # c = {**a, **b}    c = {'x': 1, 'y': 2}

        # func(**{'x': 1, 'y': 2}) 等价于 func(x=1, y=2)
        # func(**[kwargs:一个dict]) 等价于 func(**kwargs: 将一个dict解包为关键字参数)
        user = self.create_user(*args, **kwargs)
        client = APIClient()
        client.force_authenticate(user=user)
        return user, client

    def create_friendship(self, from_user, to_user):
        return FriendshipService.follow(from_user_id=from_user.id, to_user_id=to_user.id)

    def create_tweet(self, user, content=None):
        if content is None:
            content = 'default tweet content'
        return Tweet.objects.create(user=user, content=content)

    def create_comment(self, user, tweet, content=None):
        if content is None:
            content = 'default comment content'
        return Comment.objects.create(user=user, tweet=tweet, content=content)

    def create_like(self, user, target):
        # target__class__ is Comment OR Tweet
        instance, _ = Like.objects.get_or_create(
            user=user,
            content_type=ContentType.objects.get_for_model(target.__class__),
            object_id=target.id,
        )
        # 7     tweets      tweet
        # c = ContentType.objects.get(id = 7)
        # c = ContentType.objects.get_for_model(Tweet)
        # print(c)                  <ContentType: Tweets | tweet>
        # print(c.id)               7
        # print(c.app_label)        'tweets'
        # print(c.model_class())    <class 'tweets.models.Tweet'>   if c.model_class() == Tweet:
        return instance

    def create_newsfeed(self, user, tweet):
        return NewsFeed.objects.create(user=user, tweet=tweet)