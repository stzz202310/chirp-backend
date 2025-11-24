from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase as DjangoTestCase
from rest_framework.test import APIClient

from comments.models import Comment
from likes.models import Like
from tweets.models import Tweet


class TestCase(DjangoTestCase):

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
        )

    def create_tweet(self, user, content=None):
        if content is None:
            content = 'default tweet content'
        return Tweet.objects.create(user=user, content=content)

    def create_comment(self, user, tweet, content=None):
        if content is None:
            content = 'default comment content'
        return Comment.objects.create(user=user, tweet=tweet, content=content)

    def create_like(self, user, target):
        # target is comment OR tweet
        instance, _ = Like.objects.get_or_create(
            user=user,
            content_type=ContentType.objects.get_for_model(target.__class__),   # Tweet | Comment
            object_id=target.id,
        )
        # 7     tweets      tweet
        # print(content_type)           tweets | tweet
        # print(content_type.id)        7
        # print(content_type.app_label) tweets
        # print(content_type.model)     tweet
        return instance