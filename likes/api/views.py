from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

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

    @required_params(request_attr='data', params=['content_type', 'object_id',])
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
        like = serializer.save()
        return Response(
            data= LikeSerializer(instance=like).data,
            status=status.HTTP_201_CREATED
        )
    @action(methods=['POST'], detail=False)
    @required_params(request_attr='data', params=['content_type', 'object_id',])
    def cancel(self, request):
        # TODO: 前端发送 {点赞 + 取消赞}, 后端先收到 {取消赞} 后收到 {点赞}
        # 方法: 将{取消赞}缓存，收到{点赞}后 比较两者的timestamp，再决定是否执行{点赞}
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