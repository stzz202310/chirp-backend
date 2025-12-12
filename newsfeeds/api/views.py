from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.services import NewsFeedService
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination
    # TODO [HARD] NewsFeed 的界面一段时间之后会提示你有 N条新的NewsFeed，这个功能是怎么实现的？PULL(轮询)
    #   前端每隔 30 秒调用 /api/newsfeed/?id__gt=<最新ID>&only-count=True
    #   后端返回 数量, 前端显示 "你有 N 条新内容"

    # def get_queryset(self):
    #     # 自定义 queryset，因为 newsfeed 的查看是有权限的
    #     # 只能看 user=当前登录用户[request.user] 的 newsfeed
    #     # 也可以是 self.request.user.newsfeed_set.all()
    #     # 但是一般最好还是按照 NewsFeed.objects.filter 的方式写，更清晰直观
    #     return NewsFeed.objects.filter(user=self.request.user)

    def list(self, request):
        newsfeeds = NewsFeedService.get_cached_newsfeeds(user_id=request.user.id)
        page = self.paginate_queryset(queryset=newsfeeds)

        serializer = NewsFeedSerializer(
            instance=page,
            many=True,
            context={'request': request},
            # 可以向下传递到
            # class NewsFeedSerializer(...):
            #   tweet = TweetSerializer()
        )
        return self.get_paginated_response(data=serializer.data)