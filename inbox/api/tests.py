from notifications.models import Notification
from rest_framework import status

from testing.testcases import TestCase

COMMENT_URL = '/api/comments/'
LIKE_URL = '/api/likes/'
NOTIFICATION_URL = '/api/notifications/'
NOTIFICATION_DETAIL_URL = '/api/notifications/{}/'


class NotificationTests(TestCase):

    def setUp(self):
        self.clear_cache()
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


class NotificationApiTests(TestCase):

    def setUp(self):
        self.taotao, self.taotao_client = self.create_user_and_client('taotao')
        self.zhuzhu, self.zhuzhu_client = self.create_user_and_client('zhuzhu')
        self.taotao_tweet = self.create_tweet(user=self.taotao)

    def test_unread_count(self):
        data = {'content_type': 'tweet', 'object_id': self.taotao_tweet.id}
        self.zhuzhu_client.post(LIKE_URL, data=data)

        url = '/api/notifications/unread-count/'
        response = self.taotao_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 1)

        comment = self.create_comment(user=self.taotao, tweet=self.taotao_tweet)
        data = {'content_type': 'comment', 'object_id': comment.id}
        self.zhuzhu_client.post(LIKE_URL, data=data)
        response = self.taotao_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 2)

    def test_mark_all_as_read(self):
        comment = self.create_comment(user=self.taotao,tweet=self.taotao_tweet)
        data = {'content_type': 'tweet', 'object_id': self.taotao_tweet.id}
        self.zhuzhu_client.post(LIKE_URL, data=data)
        data = {'content_type': 'comment', 'object_id': comment.id}
        self.zhuzhu_client.post(LIKE_URL, data=data)

        unread_url = '/api/notifications/unread-count/'
        # 1. taotao 看到2条未读
        response = self.taotao_client.get(unread_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 2)
        # 2. zhuzhu 看到0条未读
        response = self.zhuzhu_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 0)

        mark_url = '/api/notifications/mark-all-as-read/'
        response = self.taotao_client.get(mark_url)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        # 3. zhuzhu can not mark taotao's notifications as read
        response = self.zhuzhu_client.post(mark_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_count'], 0)
        response = self.taotao_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 2)
        # 4. taotao can mark his notifications as read
        response = self.taotao_client.post(mark_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_count'], 2)
        response = self.taotao_client.get(unread_url)
        self.assertEqual(response.data['unread_count'], 0)

    def test_list(self):
        data = {'content_type': 'tweet', 'object_id': self.taotao_tweet.id}
        self.zhuzhu_client.post(LIKE_URL, data=data)
        comment = self.create_comment(user=self.taotao, tweet=self.taotao_tweet)
        data = {'content_type': 'comment', 'object_id': comment.id}
        self.zhuzhu_client.post(LIKE_URL, data=data)

        # 1. 匿名用户无法访问 api
        response = self.anonymous_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # 2. zhuzhu 看到 0 条 notifications
        response = self.zhuzhu_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 0)
        # 3. taotao 看到 2 条 notifications
        response = self.taotao_client.get(NOTIFICATION_URL)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        # 4. 标记之后 看到一个未读
        notification = self.taotao.notifications.first()
        notification.unread = False
        notification.save()
        response = self.taotao_client.get(NOTIFICATION_URL)
        self.assertEqual(response.data['count'], 2)
        # filterset_fields=('unread',) + request.query_params
        response = self.taotao_client.get(NOTIFICATION_URL, data={'unread': False})
        self.assertEqual(response.data['count'], 1)
        response = self.taotao_client.get(NOTIFICATION_URL, data={'unread': True})
        self.assertEqual(response.data['count'], 1)

    def test_update(self):
        comment = self.create_comment(user=self.taotao, tweet=self.taotao_tweet)
        self.zhuzhu_client.post(LIKE_URL, data={
            'content_type': 'tweet',
            'object_id': self.taotao_tweet.id,
        })
        self.zhuzhu_client.post(LIKE_URL, data={
            'content_type': 'comment',
            'object_id': comment.id,
        })
        notification = self.taotao.notifications.first()
        url = NOTIFICATION_DETAIL_URL.format(notification.id)

        # 1. post 不行，需要用 put
        response = self.taotao_client.post(path=url, data={'unread': False})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # 2. 不可以被匿名用户改变 notification 状态
        response = self.anonymous_client.put(path=url, data={'unread': False})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 3. 不可以被其他用户改变 notification 状态
        # 因为 get_queryset 是 filter(recipient=self.request.user 当前用户)
        # 如果 本条通知 不属于 当前用户，会返回 404 而不是 403
        response = self.zhuzhu_client.put(path=url, data={'unread': False})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # 4. 成功标记为已读
        response = self.taotao_client.put(path=url, data={'unread': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        unread_url = '/api/notifications/unread-count/'
        response = self.taotao_client.get(path=unread_url)
        self.assertEqual(response.data['unread_count'], 1)

        # 5. 再标记为未读
        response = self.taotao_client.put(path=url, data={'unread': True})
        response = self.taotao_client.get(path=unread_url)
        self.assertEqual(response.data['unread_count'], 2)

        # 6. 必须带 unread
        response = self.taotao_client.put(path=url, data={'verb': 'newverb'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # 7. 不可修改其他的信息
        response = self.taotao_client.put(path=url, data={'verb': 'newverb', 'unread': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertNotEqual(notification.verb, 'newverb')