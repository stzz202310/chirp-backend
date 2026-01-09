from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from friendships.api.serializers import (
    FollowingSerializer,
    FollowerSerializer,
    FriendShipSerializerForCreate,
)
from friendships.models import Friendship, HBaseFollowing, HBaseFollower
from friendships.services import FriendshipService
from gatekeeper.models import GateKeeper
from utils.paginations import EndlessPagination


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
    pagination_class = EndlessPagination

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    # GET /api/friendships/{pk}/followers/  GET {pk} 的粉丝列表
    def followers(self, request, pk):
        # self.paginator: DRF 基于 pagination_class 创建的, 已绑定上下文的分页实例
        # 统一通过 self.paginator 调用分页相关方法
        pk = int(pk)
        user = self.get_object()
        paginator = self.paginator
        if GateKeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
            page = paginator.paginate_hbase(hb_model=HBaseFollower, row_key_prefix=(pk,), request=request)
        else:
            friendships = Friendship.objects.filter(to_user_id=pk).order_by('-created_at')
            page = paginator.paginate_queryset(queryset=friendships, request=request)

        # page: 当前页的 instances 集合 (list 或 queryset)
        serializer = FollowerSerializer(instance=page, many=True, context={'request': request})
        return paginator.get_paginated_response(data=serializer.data)   # 返回当前页

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followings(self, request, pk):  # GET {pk} 的关注列表
        pk = int(pk)
        user = self.get_object()
        paginator = self.paginator
        if GateKeeper.is_switch_on(gk_name='switch_friendship_to_hbase'):
            page = paginator.paginate_hbase(hb_model=HBaseFollowing, row_key_prefix=(pk,), request=request)
        else:
            friendships = Friendship.objects.filter(from_user_id=pk).order_by('-created_at')
            page = paginator.paginate_queryset(queryset=friendships, request=request)

        serializer = FollowingSerializer(instance=page, many=True, context={'request': request})
        return paginator.get_paginated_response(data=serializer.data)

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    def follow(self, request, pk):
        # 注意 pk 的类型是 str, 所以要做类型转换 int(pk)
        # get_object_or_404(): check if ⚠️User (not Friendship) with id=pk exists
        from_user_id = request.user.id
        to_user_id = int(pk)
        follow_user = self.get_object()

        # 特殊判断重复 follow 的情况（比如前端猛点好多少次 follow)
        # 静默处理，不报错，因为这类重复操作因为网络延迟的原因会比较多，没必要当做错误处理
        if FriendshipService.has_followed(from_user_id=from_user_id, to_user_id=to_user_id):
            return Response(
                data={'success': True, 'duplicate': True},
                status=status.HTTP_201_CREATED,
            )

        serializer = FriendShipSerializerForCreate(data={
            'from_user_id': from_user_id,
            'to_user_id': to_user_id,   # follow_user.id
        })
        if not serializer.is_valid():
            # [serializers.ModelSerializer] serializer.validate() 会校验模型约束，
            # 其中包括 unique_together = (('from_user', 'to_user'),)
            # 用于防止同一对用户关系被重复创建
            return Response(data={
                'success': False,
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        friendship = serializer.save()
        # /localhost/admin/ 如果对 Friendship 进行修改，则无法触发 '删除缓存'
        # FriendshipService.invalidate_following_cache(request.user.id)
        return Response(
            data=FollowingSerializer(instance=friendship, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    def unfollow(self, request, pk):
        from_user_id = request.user.id
        unfollow_user = self.get_object()

        if from_user_id == unfollow_user.id:    # int(pk)
            return Response(data={
                'success': False,
                'message': 'You cannot unfollow yourself',
            }, status=status.HTTP_400_BAD_REQUEST,)

        deleted = FriendshipService.unfollow(from_user_id=from_user_id, to_user_id=unfollow_user.id)
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