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
    # TODO [HARD] NewsFeed 的界面一段时间之后会提示你有 N条新的NewsFeed，这个功能是怎么实现的？PULL(轮询)
    #   前端每隔 30 秒调用 /api/newsfeed/?id__gt=<最新ID>&only-count=True
    #   后端返回 数量, 前端显示 "你有 N 条新内容"

    def get_queryset(self):
        # 自定义 queryset，因为 newsfeed 的查看是有权限的
        # 只能看 user=当前登录用户[request.user] 的 newsfeed
        # 也可以是 self.request.user.newsfeed_set.all()
        # 但是一般最好还是按照 NewsFeed.objects.filter 的方式写，更清晰直观
        return NewsFeed.objects.filter(user=self.request.user)

    @method_decorator(ratelimit(key='user', rate='5/s', method='GET', block=True))
    def list(self, request):
        paginator = self.paginator
        cached_newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=request.user.id)
        # 自定义方法，需要通过 self.paginator 调用
        page = paginator.paginate_cached_list(
            cached_list=cached_newsfeeds,
            request=request,
        )

        if page is None:    # 说明可能存在未加载到 cache 的数据，需要直接查询数据库
            if GateKeeper.is_switch_on(gk_name='switch_newsfeed_to_hbase'):
                page = paginator.paginate_hbase(
                    hb_model=HBaseNewsFeed,
                    row_key_prefix=(request.user.id,),
                    request=request
                )
            else:
                # queryset = NewsFeed.objects.filter(user=request.user)
                queryset = self.get_queryset()
                # self.paginate_queryset(): 会自动传入 request=self.request
                # self.paginator.paginate_queryset(): 需要手动传入 request
                page = paginator.paginate_queryset(queryset=queryset, request=request)

        serializer = NewsFeedSerializer(
            instance=page,
            many=True,
            context={'request': request},
            # 可以向下传递到
            # class NewsFeedSerializer(...):
            #   tweet = TweetSerializer()
        )
        return paginator.get_paginated_response(data=serializer.data)