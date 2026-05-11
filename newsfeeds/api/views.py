from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from gatekeeper.models import GateKeeper
from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed, HBaseNewsFeed
from newsfeeds.services import NewsFeedService
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    def get_queryset(self):
        # 只能查看当前登录用户自己的新鲜事列表
        return NewsFeed.objects.filter(user=self.request.user)

    @method_decorator(ratelimit(key='user', rate='5/s', method='GET', block=True))
    def list(self, request):
        paginator = self.paginator
        # 1. 优先从 Redis cache 读取
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=request.user.id)
        # 自定义方法，需要通过 self.paginator 调用
        page = paginator.paginate_cached_list(cached_list=cached_newsfeeds, request=request)

        # 2. cache 不足, 回源数据库
        if page is None:
            if GateKeeper.is_switch_on(gk_name='switch_newsfeed_to_hbase'):
                page = paginator.paginate_hbase(
                    hb_model=HBaseNewsFeed,
                    row_key_prefix=(request.user.id,),
                    request=request
                )
            else:
                queryset = self.get_queryset()
                page = paginator.paginate_queryset(queryset=queryset, request=request)

        serializer = NewsFeedSerializer(
            instance=page,
            many=True,
            context={'request': request},   # context 会向下传递到 TweetSerializer
        )
        return paginator.get_paginated_response(data=serializer.data)