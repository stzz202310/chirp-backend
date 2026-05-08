from django.utils.decorators import method_decorator
from notifications.models import Notification
from ratelimit.decorators import ratelimit
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.api.serializers import (
    NotificationSerializer,
    NotificationSerializerForUpdate,
)
from utils.decorators import required_params


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
        return Notification.objects.filter(recipient=self.request.user)

    @action(methods=['GET'], detail=False, url_path='unread-count')
    @method_decorator(ratelimit(key='user', rate='3/s', method='GET', block=True))
    def unread_count(self, request, *args, **kwargs):
        # ❌ queryset = self.filter_queryset(queryset=self.get_queryset())
        # 因为DRF 只会根据 request.query_params, 不会根据 request.data 自动生成过滤条件
        count = self.get_queryset().filter(unread=True).count()
        return Response(data={'unread_count': count}, status=status.HTTP_200_OK,)

    @action(methods=['POST'], detail=False, url_path='mark-all-as-read')
    @method_decorator(ratelimit(key='user', rate='3/s', method='POST', block=True))
    def mark_all_as_read(self, request, *args, **kwargs):
        updated_count = self.get_queryset().filter(unread=True).update(unread=False)
        return Response(data={'marked_count': updated_count}, status=status.HTTP_200_OK,)

    @required_params(method='PUT', params=['unread',])
    @method_decorator(ratelimit(key='user', rate='3/s', method='POST', block=True))
    def update(self, request, *args, **kwargs):
        serializer = NotificationSerializerForUpdate(
            instance=self.get_object(),
            data=request.data,
        )
        if not serializer.is_valid():
            return Response(data={
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        notification = serializer.save()
        serializer = NotificationSerializer(instance=notification)
        return Response(data=serializer.data, status=status.HTTP_200_OK,)