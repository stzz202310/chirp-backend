from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from tweets.models import Tweet
from utils.time_helpers import utc_now


class TweetTests(TestCase):

    def test_hours_to_now(self):
        taotao = User.objects.create_user(username='taotao')
        tweet = Tweet.objects.create(user=taotao, content='Hello Zhuzhu')
        tweet.created_at = utc_now() -timedelta(hours=10)
        tweet.save()
        self.assertEqual(tweet.hours_to_now, 10)
