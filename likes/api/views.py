from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from inbox.services import NotificationService
from likes.api.serializers import (
    LikeSerializer,
    LikeSerializerForCreate,
    LikeSerializerForCancel,
)
from likes.models import Like
from utils.decorators import required_params


class LikeViewSet(viewsets.GenericViewSet):
    queryset = Like.objects.all()
    serializer_class = LikeSerializerForCreate
    permission_classes = [IsAuthenticated]

    @required_params(method='POST', params=['content_type', 'object_id',])
    def create(self, request, *args, **kwargs):
        serializer = LikeSerializerForCreate(
            data=request.data,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response(data={
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        like, created = serializer.get_or_create()
        if created: # 重复点赞 静默处理, 不要发多条 notification
            NotificationService.send_like_notification(like=like)
        return Response(
            data= LikeSerializer(instance=like).data,
            status=status.HTTP_201_CREATED
        )
    @action(methods=['POST'], detail=False)
    @required_params(method='POST', params=['content_type', 'object_id',])
    def cancel(self, request):
        # TODO [HARD]: 前端发送 {点赞 + 取消赞}, 后端先收到 {取消赞} 后收到 {点赞}
        # 方法: 将{取消赞}缓存，收到{点赞}后 比较两者的timestamp，再决定是否执行{点赞}
        # 数据库无法实现 先取消 再点赞，所以用 cache
        # if deleted_entries = 0:
        #   cache.set('pre_cancel_like::tweet::1::user::2', True, timeout=1)
        #   {user 2} precancel {tweet 1}, 1s 内有效
        #
        # def create() 点赞
        #   1. 检查 cache
        #   2. 如果有{取消本条赞}，则取消本次操作 [并删除本条cache]

        serializer = LikeSerializerForCancel(
            data=request.data,
            context={'request': request},
        )
        if not serializer.is_valid():
            return Response(data={
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        deleted, rows_count = serializer.cancel()
        return Response(data={
            'success': True,
            'deleted': deleted,
            'rows_count': rows_count,
        }, status=status.HTTP_200_OK)