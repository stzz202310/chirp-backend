from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.cache import caches
from django.test import TestCase as DjangoTestCase
from rest_framework.test import APIClient

from comments.models import Comment
from likes.models import Like
from newsfeeds.models import NewsFeed
from tweets.models import Tweet

"""
create {comment, tweet, like, newsfeed}
1. 前端要求创建 via API
2. 测试要求创建 via testcases.create_tweet(user=user)
"""
class TestCase(DjangoTestCase):

    def clear_cache(self):
        caches['testing'].clear()

    @property
    def anonymous_client(self):
        # return APIClient() 每次调用 anonymous_client 都会创建一个新的实例
        # 在当前测试用例实例上缓存一个 _anonymous_client, 实现 APIClient 单例复用
        # 类似地，QuerySet 在 Django 内部也有 instance 级别的缓存机制
        if hasattr(self, '_anonymous_client'):
            # hasattr(obj, key)
            # getattr(obj, key, default=None)
            # setattr(obj, key, value)
            return self._anonymous_client
        self._anonymous_client = APIClient()
        return self._anonymous_client

    def create_user(self, username, email=None, password=None):
        if password is None:
            password = 'generic password'
        if email is None:
            email = f'{username}@zhuzhu.com'
        return User.objects.create_user(    # .create_user()
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
        # a = {'x': 1}, b = {'y', 2}
        # c = [a, b]        c = [{'x': 1}, {'y': 2}]
        # c = {*a, *b}      c = {'x', 'y'}
        # c = {**a, **b}    c = {'x': 1, 'y': 2}
        user = self.create_user(*args, **kwargs)
        client = APIClient()
        client.force_authenticate(user=user)
        return user, client

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