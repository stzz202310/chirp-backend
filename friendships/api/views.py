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
    # ⚠️ queryset 必须设为 User.objects.all(), 若设为 Friendship.objects.all() 可能会返回 404
    # 例: detail=True 的 action 会先调用 get_object() | queryset.filter(pk=<id>) 来验证对象是否存在
    queryset = User.objects.all()
    serializer_class = FriendShipSerializerForCreate
    pagination_class = EndlessPagination

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followers(self, request, pk):
        # self.paginator: DRF 基于 pagination_class 创建的分页实例, 可直接调用分页相关方法
        paginator = self.paginator
        pk = int(pk)
        user = self.get_object()
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
    def followings(self, request, pk):
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
        # pk 的类型是 str, 所以要做类型转换 int(pk)
        # self.get_object_or_404(): check if User (not Friendship) with id=pk exists
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
            return Response(data={
                'success': False,
                'message': 'Please check input.',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        friendship = serializer.save()
        return Response(
            data=FollowingSerializer(instance=friendship, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    def unfollow(self, request, pk):
        from_user_id = request.user.id
        unfollow_user = self.get_object()

        if from_user_id == unfollow_user.id:
            return Response(data={
                'success': False,
                'message': 'You cannot unfollow yourself',
            }, status=status.HTTP_400_BAD_REQUEST,)

        deleted = FriendshipService.unfollow(from_user_id=from_user_id, to_user_id=unfollow_user.id)
        return Response(data={'success': True, 'deleted': deleted,})

    def list(self, request):
        return Response(data={'message': 'this is friendships home page'})