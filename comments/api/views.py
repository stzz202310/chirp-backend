from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from comments.api.permissions import IsObjectOwner
from comments.api.serializers import (
    CommentSerializer,
    CommentSerializerForCreate,
    CommentSerializerForUpdate,
)
from comments.models import Comment
from utils.decorators import required_params


class CommentViewSet(viewsets.GenericViewSet):
    """
    只实现 list, create, update, destroy 的方法
    不实现 retrieve (查询单个 comment) 的方法，因为没有这个需求
    """
    # DRF界面: 基于 {serializer_class} 展示|渲染 表单
    # queryset: self.get_object()
    serializer_class = CommentSerializerForCreate
    queryset = Comment.objects.all()
    filterset_fields = ('tweet_id',)

    def get_permissions(self):
    # 需要实例化权限类，例如 AllowAny() 或 IsAuthenticated()
    # 不能写成 AllowAny 或 IsAuthenticated（那只是类名，而不是权限实例）
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action in ['update', 'destroy',]:
            # 先检查 是否登陆，再检查 request.user == comment的owner
            return [IsAuthenticated(), IsObjectOwner()]
        return [AllowAny()]

    @required_params(request_attr='query_params', params=['tweet_id'])
    def list(self, request, *args, **kwargs):
        # tweet_id = request.query_params.get('tweet_id')
        # comments = Comment.objects.filter(tweet_id=tweet_id)
        queryset = self.get_queryset()
        # select_related [join]; null [n + 1 queries]
        comments = self.filter_queryset(queryset=queryset)\
            .prefetch_related('user')\
            .order_by('created_at')
        # 1. 检查视图中是否配置 filter_backends
        # 2. 依次调用每个 filter backend 的 filter_queryset 方法 [DjangoFilterBackend]
        #    DjangoFilterBackend: 它会根据 filterset_fields 去过滤 queryset
        #    DRF 会根据 request.query_params 自动生成过滤条件
        # 3. 返回经过所有过滤器处理后的 queryset
        serializer = CommentSerializer(
            instance=comments,
            many=True,
            context={'request': request},
        )
        return Response(
            data={'comments': serializer.data},
            status=status.HTTP_200_OK,
        )

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

        comment = serializer.save()
        return Response(data=CommentSerializer(
            instance=comment,
            context={'request': request},
        ).data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        # get_object 是 DRF 包装的一个函数，会在找不到的时候 raise 404 error
        # 所以这里不需要做额外的判断
        comment = self.get_object()
        serializer = CommentSerializerForUpdate(
            instance=comment, # self.get_object()
            data=request.data,
        )   # 不同的需求，用不同的 Serializer —— 更安全、隔离、解耦

        if not serializer.is_valid():
            return Response(data={
                'message': 'Please check input.',
            }, status=status.HTTP_400_BAD_REQUEST)
        # save() 方法会触发 serializer 中的 update 方法，点进 save 的具体实现里可以看到
        # save() 会根据是否传入 instance 来决定执行 create() 还是 update()
        comment = serializer.save()
        return Response(data=CommentSerializer(
            instance=comment,
            context={'request': request},
        ).data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        comment = self.get_object()
        comment.delete()
        # DRF 里默认 destroy 返回的是 status=status.HTTP_204_NO_CONTENT
        # 这里 return 了 success=True 更直观的让前端去做判断，所以 return 200 更合适
        return Response(data={'success': True}, status=status.HTTP_200_OK)
