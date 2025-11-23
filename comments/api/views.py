from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from comments.api.serializers import (
    CommentSerializer,
    CommentSerializerForCreate,
)
from comments.models import Comment


class CommentViewSet(viewsets.GenericViewSet):
    """
    只实现 list, create, update, destroy 的方法
    不实现 retrieve (查询单个 comment) 的方法，因为没有这个需求
    """
    # DRF界面: 基于 {serializer_class} 展示|渲染 表单
    # queryset: self.get_object()
    serializer_class = CommentSerializerForCreate
    queryset = Comment.objects.all()

    def get_permissions(self):
    # 需要实例化权限类，例如 AllowAny() 或 IsAuthenticated()
    # 不能写成 AllowAny 或 IsAuthenticated（那只是类名，而不是权限实例）
        if self.action == 'create':
            return [IsAuthenticated()]
        # allow = AllowAny() return allow
        return [AllowAny()]

    def create(self, request, *args, **kwargs):
        data = {
            'user_id': request.user.id,
            'tweet_id': request.data.get('tweet_id'),
            'content': request.data.get('content'),
        }
        # 注意这里必须要加 'data=' 来指定参数是传给 data 的
        # 因为默认的第一个参数是 instance
        serializer = CommentSerializerForCreate(data=data)
        if not serializer.is_valid():
            return Response(data={
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        # save 方法会触发 serializer 中的 create方法，点进 save 的具体实现里可以看到
        comment = serializer.save()
        return Response(
            data=CommentSerializer(instance=comment).data,
            status=status.HTTP_201_CREATED,
        )