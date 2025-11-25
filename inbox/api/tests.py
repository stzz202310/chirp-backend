from testing.testcases import TestCase
from notifications.models import Notification


COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'


class NotificationTests(TestCase):

    def setUp(self):
        self.taotao, self.taotao_client = self.create_user_and_client('taotao')
        self.zhuzhu, self.zhuzhu_client = self.create_user_and_client('zhuzhu')
        self.zhuzhu_tweet = self.create_tweet(user=self.zhuzhu)

    def test_comment_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        data = {'tweet_id': self.zhuzhu_tweet.id, 'content': 'zhuzhu zai xi zao',}
        self.taotao_client.post(COMMENT_URL, data=data)
        self.assertEqual(Notification.objects.count(), 1)

    def test_like_create_api_trigger_notification(self):
        self.assertEqual(Notification.objects.count(), 0)
        data = {'content_type': 'tweet', 'object_id': self.zhuzhu_tweet.id,}
        self.taotao_client.post(LIKE_URL, data=data)
        self.assertEqual(Notification.objects.count(), 1)