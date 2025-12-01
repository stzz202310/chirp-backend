from notifications.models import Notification
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.api.serializers import NotificationSerializer


class NotificationViewSet(
    viewsets.GenericViewSet,
    viewsets.mixins.ListModelMixin, # 自带翻页机制: count, next, previous, results
):
    serializer_class = NotificationSerializer
    permission_classes = (IsAuthenticated,)
    filterset_fields=('unread',)
    # queryset = Notification.objects.filter(recipient=self.request.user)
    # ❌ name 'self' is not defined: queryset 是类属性，在加载类时执行，没有 self

    def get_queryset(self):
        # recipient = models.ForeignKey(
        #   settings.AUTH_USER_MODEL,           可以在 twitter.settings 中自定义 user
        #   related_name='notifications', ...)  user.notifications 自定义 | user.notification_set 默认
        # return self.request.user.notifications.all()
        """
        request vs self.request
        1. DRF 的 action 方法是作为“普通方法”被调用的，需要显式接收 request 参数
           def unread_count(self, request, *args, **kwargs):
        2. self.request 是 DRF 在 dispatch 时设置的属性 self.request = request
           方便在 ViewSet 的其他方法中访问 def get_queryset(self)
        """
        return Notification.objects.filter(recipient=self.request.user)

    @action(methods=['GET'], detail=False, url_path='unread-count')
    def unread_count(self, request, *args, **kwargs):
        # GET /api/notifications/unread-count/
        count = self.get_queryset().filter(unread=True).count()
        return Response(
            data={'unread_count': count},
            status=status.HTTP_200_OK,
        )

    @action(methods=['POST'], detail=False, url_path='mark-all-as-read')
    def mark_all_as_read(self, request, *args, **kwargs):
        # N + 1 queries
        # for notification in self.get_queryset().filter(unread=True):
        #     notification.unread = False
        #     notification.save()

        # POST /api/notifications/mark-all-as-read/

        # .filter(recipient=self.request.user).filter(unread=True)
        # index_together = ('recipient', 'unread')
        # ⚠️.filter().filter(): 需要建立 联合索引
        updated_count = self.get_queryset().filter(unread=True).update(unread=False)
        return Response(
            data={'marked_count': updated_count},
            status=status.HTTP_200_OK,
        )