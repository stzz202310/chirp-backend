from notifications.models import Notification

from inbox.services import NotificationService
from testing.testcases import TestCase


class NotificationServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.taotao = self.create_user('taotao')
        self.zhuzhu = self.create_user('zhuzhu')
        self.taotao_tweet = self.create_tweet(user=self.taotao)
        self.zhuzhu_comment = self.create_comment(user=self.zhuzhu,tweet=self.taotao_tweet)

    def test_send_comment_notification(self):
        # 1. do not dispatch notification if tweet user == comment on tweet user
        comment = self.create_comment(user=self.taotao, tweet=self.taotao_tweet)
        NotificationService.send_comment_notification(comment=comment)
        self.assertEqual(Notification.objects.count(), 0)

        # 2. dispatch notification if tweet user != comment on tweet user
        comment = self.create_comment(user=self.zhuzhu, tweet=self.taotao_tweet)
        NotificationService.send_comment_notification(comment=comment)
        self.assertEqual(Notification.objects.count(), 1)

    def test_send_like_notification(self):
        # 1. do not dispatch notification if tweet user = like tweet user
        like = self.create_like(user=self.taotao, target=self.taotao_tweet)
        NotificationService.send_like_notification(like=like)
        self.assertEqual(Notification.objects.count(), 0)

        # 2. dispatch notification if tweet user != like tweet user
        like = self.create_like(user=self.zhuzhu, target=self.taotao_tweet)
        NotificationService.send_like_notification(like=like)
        self.assertEqual(Notification.objects.count(), 1)

        # 3. do not dispatch notification if comment user = like comment user
        like = self.create_like(user=self.zhuzhu, target=self.zhuzhu_comment)
        NotificationService.send_like_notification(like=like)
        self.assertEqual(Notification.objects.count(), 1)

        # 4. dispatch notification if comment user != like comment user
        like = self.create_like(user=self.taotao, target=self.zhuzhu_comment)
        NotificationService.send_like_notification(like=like)
        self.assertEqual(Notification.objects.count(), 2)