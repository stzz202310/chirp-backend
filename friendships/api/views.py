from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from friendships.api.serializers import (
    FollowingSerializer,
    FollowerSerializer,
    FriendShipSerializerForCreate,
)
from friendships.models import Friendship
from utils.paginations import FriendshipPagination


class FriendshipViewSet(viewsets.GenericViewSet):
    # POST /api/friendship/1/follow/    当前用户关注 follow   user_id=1 的用户
    # POST /api/friendship/1/unfollow/  当前用户取关 unfollow user_id=1 的用户

    # 因此这里 queryset 需要是 User.objects.all()
    # 如果是 Friendship.objects.all() 的话就会出现 404 Not Found
    # 因为 detail=True 的 actions 会默认先去调用 get_object() 也就是
    # queryset.filter(pk=1) 查询一下这个 object 在不在
    queryset = User.objects.all()
    serializer_class = FriendShipSerializerForCreate
    # 一般来说，不同的 views 所需要的 pagination 规则肯定是不同的，因此一般都需要自定义
    pagination_class = FriendshipPagination

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followers(self, request, pk):
        # GET /api/friendships/{pk}/followers/  GET {pk} 的粉丝列表
        friendships = Friendship.objects.filter(to_user_id=pk)
        # self.paginator: 根据 pagination_class 新建的属性
        # def paginate_queryset(self, queryset):
        #   if self.paginator is None: return None
        #   return self.paginator.paginate_queryset(queryset, self.request, view=self)
        page = self.paginate_queryset(queryset=friendships)
        serializer = FollowerSerializer(instance=page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followings(self, request, pk):  # GET {pk} 的关注列表
        friendships = Friendship.objects.filter(from_user_id=pk)
        page = self.paginate_queryset(queryset=friendships)
        serializer = FollowingSerializer(instance=page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data) # 返回当前页

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def follow(self, request, pk):
        # 特殊判断重复 follow 的情况（比如前端猛点好多少次 follow)
        # 静默处理，不报错，因为这类重复操作因为网络延迟的原因会比较多，没必要当做错误处理
        # if Friendship.objects.filter(from_user=request.user, to_user=pk).exists():
        #     return Response({
        #         'success': True,
        #         'duplicate': True,
        #     }, status=status.HTTP_201_CREATED)

        # get_object_or_404(): check if user with id=pk exists
        follow_user = self.get_object()
        serializer = FriendShipSerializerForCreate(data={
            'from_user_id': request.user.id,
            'to_user_id': follow_user.id, # pk
        })
        if not serializer.is_valid():
            return Response(data={
                'success': False,
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        friendship = serializer.save()
        return Response(
            data=FollowingSerializer(
                instance=friendship,
                context={'request': request}
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    def unfollow(self, request, pk):
        unfollow_user = self.get_object()
        # 注意 pk 的类型是 str, 所以要做类型转换 int(pk)
        if request.user.id == unfollow_user.id:
            return Response(data={
                'success': False,
                'message': 'You cannot unfollow yourself',
            }, status=status.HTTP_400_BAD_REQUEST,)

        # Queryset 的 delete 操作返回两个值，一个是删了多少数据，一个是具体每种类型删了多少
        deleted, _ = Friendship.objects.filter(
            from_user=request.user,
            to_user=unfollow_user,
        ).delete()  # 没有 follow 的情况下 unfollow 静默处理
        return Response(data={'success': True, 'deleted': deleted,})

    def list(self, request):
        # 只有定义了 list() 的 ViewSet 才会出现在 localhost 根目录中
        # ModelViewSet, ReadOnlyModelViewSet: 已定义 list()
        # GenericViewSet: 需要自定义 list()
        return Response(data={'message': 'this is friendships home page'})

        # # [Optional]
        # # 1. GET /api/friendships/?type=following&from_user_id=1    查询某个用户的关注列表
        # # 2. GET /api/friendships/?type=follower&to_user_id=1       查询某个用户的粉丝列表
        # # 3. GET /api/friendships/?from_user_id=1&to_user_id=2      查询两个人之间是否存在关注关系
        #
        # query_params = request.query_params
        # follow_type = query_params.get('type')
        # from_user_id = query_params.get('from_user_id')
        # to_user_id = query_params.get('to_user_id')
        #
        # if follow_type == 'following' and from_user_id:
        #     friendships = Friendship.objects.filter(from_user_id=from_user_id)
        #     serializer = FollowingSerializer(instance=friendships, many=True)
        #     return Response(
        #         data={'followings': serializer.data},
        #         status=status.HTTP_200_OK,
        #     )
        #
        # if follow_type == 'follower' and to_user_id:
        #     friendships = Friendship.objects.filter(to_user_id=to_user_id)
        #     serializer = FollowerSerializer(instance=friendships, many=True)
        #     return Response(
        #         data={'followers': serializer.data},
        #         status=status.HTTP_200_OK,
        #     )
        #
        # if from_user_id and to_user_id:
        #     friendship = Friendship.objects.filter(from_user_id=from_user_id, to_user_id=to_user_id)
        #     from_user_username = User.objects.get(id=from_user_id).username
        #     to_user_username = User.objects.get(id=to_user_id).username
        #
        #     if not friendship.exists():
        #         return Response(
        #             data={"message": f'{from_user_username} does not follow {to_user_username}'},
        #             status = status.HTTP_200_OK,
        #         )
        #     return Response(
        #         data={"message": f'{from_user_username} follows {to_user_username}'},
        #         status=status.HTTP_200_OK,
        #     )
        #
        # return Response(
        #     data={'error': 'Missing parameters'},
        #     status=status.HTTP_400_BAD_REQUEST,
        # )