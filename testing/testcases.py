from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.test import TestCase as DjangoTestCase
from rest_framework.test import APIClient

from comments.models import Comment
from django_hbase.models import HBaseModel
from friendships.services import FriendshipService
from gatekeeper.models import GateKeeper
from likes.models import Like
from newsfeeds.services import NewsFeedService
from tweets.models import Tweet
from utils.redis_client import RedisClient


class TestCase(DjangoTestCase):

    hbase_tables_created = False

    def setUp(self):
        self.clear_cache()
        if not getattr(settings, 'HBASE_ENABLED', True):
            return
        try:
            self.hbase_tables_created = True
            for hbase_model_class in HBaseModel.__subclasses__():
                hbase_model_class.create_table()
        except Exception:
            self.tearDown()
            raise

    def tearDown(self):
        if not self.hbase_tables_created:
            return
        if not getattr(settings, 'HBASE_ENABLED', True):
            return
        for hbase_model_class in HBaseModel.__subclasses__():
            hbase_model_class.drop_table()

    def clear_cache(self):
        caches['testing'].clear()
        RedisClient.clear() # ⚠️ 测试环境: Redis/Gatekeeper/Celery 的数据都会被清空
        if getattr(settings, 'HBASE_ENABLED', True):
            GateKeeper.turn_on(gk_name='switch_newsfeed_to_hbase')
            GateKeeper.turn_on(gk_name='switch_friendship_to_hbase')

    @property
    def anonymous_client(self):
        # return APIClient() 每次调用 anonymous_client 都会创建一个新的实例
        # 在当前测试用例实例上缓存一个 _anonymous_client, 实现 APIClient 单例复用
        # 类似地，QuerySet 在 Django 内部也有 instance 级别的缓存机制
        if hasattr(self, '_anonymous_client'):
            return self._anonymous_client
        self._anonymous_client = APIClient()
        return self._anonymous_client

    def create_user(self, username, email=None, password=None):
        if password is None:
            password = 'generic password'
        if email is None:
            email = f'{username}@zhuzhu.com'
        return User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )   # ⚠️ 不会自动创建关联的 UserProfile, 需显式访问 user.profile

    def create_user_and_client(self, *args, **kwargs):
        user = self.create_user(*args, **kwargs)

        # APIClient 是 DRF 提供的测试客户端
        # - 类似于"模拟一个浏览器/HTTP 客户端"
        # - 用于在测试中发起 API 请求 (GET / POST / PUT 等)
        client = APIClient()

        # - 在测试中强制将请求视为「已登录状态」
        # - 直接绕过认证流程（不走 login / token / session）
        # - 后续通过该 client 发出的请求，request.user 都是该 user
        client.force_authenticate(user=user)
        return user, client

    def create_friendship(self, from_user, to_user):
        return FriendshipService.follow(from_user_id=from_user.id, to_user_id=to_user.id)

    def create_newsfeed(self, user, tweet):
        created_at = NewsFeedService.created_at(tweet=tweet)
        return NewsFeedService.create(user_id=user.id, tweet_id=tweet.id, created_at=created_at)

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
            content_type=ContentType.objects.get_for_model(model=target.__class__),
            object_id=target.id,
        )
        return instance