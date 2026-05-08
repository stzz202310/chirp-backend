from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from comments.api.serializers import (
    CommentSerializer,
    CommentSerializerForCreate,
    CommentSerializerForUpdate,
)
from comments.models import Comment
from inbox.services import NotificationService
from utils.decorators import required_params
from utils.permissions import IsObjectOwner, IsCommentOwnerOrTweetOwner


class CommentViewSet(viewsets.GenericViewSet):
    """
    只实现 list, create, update, destroy 的方法
    不实现 retrieve (查询单个 comment) 的方法，因为没有这个需求
    """
    serializer_class = CommentSerializerForCreate
    queryset = Comment.objects.all()
    filterset_fields = ('tweet_id',)

    def get_permissions(self):
        # 必须返回一个 list, 里面是 权限类的实例  ✅ [AllowAny()]
        # 不能直接返回类名, 这只是类本身          ❌ [AllowAny]
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action == 'update':
            # 1. 检查 IsAuthenticated() [是否登陆]
            # 2. 检查 IsObjectOwner() [只允许 {评论作者: comment.user} 修改评论]
            return [IsAuthenticated(), IsObjectOwner()]
        if self.action == 'destroy':
            # 2. 检查 IsCommentOwnerOrTweetOwner()
            #    允许 {评论作者：comment.user} {推特作者：comment.tweet.user} 删除评论
            return [IsAuthenticated(), IsCommentOwnerOrTweetOwner()]
        return [AllowAny()]

    @required_params(method='GET', params=['tweet_id']) # ⚠️ 检测是否有 tweet_id, 否则会返回所有的评论
    @method_decorator(ratelimit(key='user', rate='3/min', method='GET', block=True))
    # TODO [Homework] 有权限看这个tweet的用户, 才有权限看这个tweet的评论
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        comments = self.filter_queryset(queryset=queryset).order_by('created_at')

        serializer = CommentSerializer(
            instance=comments,
            many=True,
            context={'request': request},
        )
        return Response(
            data={'comments': serializer.data},
            status=status.HTTP_200_OK,
        )

    @method_decorator(ratelimit(key='user', rate='3/s', method='POST', block=True))
    def create(self, request, *args, **kwargs):
        data = {
            'user_id': request.user.id,
            'tweet_id': request.data.get('tweet_id'),
            'content': request.data.get('content'),
        }
        serializer = CommentSerializerForCreate(data=data)
        if not serializer.is_valid():
            return Response(data={
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        comment = serializer.save()
        NotificationService.send_comment_notification(comment=comment)
        serializer = CommentSerializer(
            instance=comment,
            context={'request': request},
        )
        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED,
        )

    @method_decorator(ratelimit(key='user', rate='3/s', method='POST', block=True))
    def update(self, request, *args, **kwargs):
        comment = self.get_object()
        serializer = CommentSerializerForUpdate(instance=comment, data=request.data)

        if not serializer.is_valid():
            return Response(data={
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        comment = serializer.save()
        serializer = CommentSerializer(instance=comment, context={'request': request})
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @method_decorator(ratelimit(key='user', rate='5/s', method='POST', block=True))
    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        comment.delete()
        return Response(data={'success': True}, status=status.HTTP_200_OK)