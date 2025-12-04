from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class EndlessPagination(PageNumberPagination):
    page_size = 20

    def __init__(self):
        # 调用父类构造函数，维持 DRF 的正常逻辑
        # 可省略: PageNumberPagination, BasePagination 没有定义 __init__
        # super(EndlessPagination, self).__init__()
        self.has_next_page = False  # 增加一个实例属性 has_next_page

    def to_html(self):  # 用于 浏览器模式下分页 HTML 展示 [但现实里 DRF 很少用它]
        pass            # 不需要 HTML 输出, 只输出 JSON

    def paginate_queryset(self, queryset, request, view=None):
        if 'created_at__gt' in request.query_params:
            # [顶部]下拉刷新 Pull-to-Refresh
            # created_at__gt 用于下拉刷新的时候加载[所有]最新的内容进来
            # 为了简单起见，下拉刷新不做翻页机制，直接加载所有更新的数据
            # 因为如果数据很久没有更新的话，不会采用下拉刷新的方式进行更新，而是重新加载最新的数据
            created_at__gt = request.query_params['created_at__gt']
            queryset = queryset.filter(created_at__gt=created_at__gt)
            self.has_next_page = False  # 所有最新数据，因此没有下一页
            return queryset.order_by('-created_at')

        if 'created_at__lt' in request.query_params:
            # [底部]上拉加载更多 Load More
            # created_at__lt 用于向上滚屏 (往下翻页) 的时候加载下一页的数据
            # 寻找 created_at < created_at__lt 的 objects 里按照 created_at 倒序的
            # 前 page_size + 1 个 objects
            # 比如目前的 created_at 列表是 [10, 9, 8, 7, ... 1]
            # 如果 created_at__lt=10, page_size=2 则应该返回 [9, 8, 7], 多返回一个 object 的
            # 原因是为了判断是否还有下一页从而减少一次空加载|空刷
            created_at__lt = request.query_params['created_at__lt']
            queryset = queryset.filter(created_at__lt=created_at__lt)

        # 请求没有带参数: 默认访问首页
        queryset = queryset.order_by('-created_at')[:self.page_size + 1]
        self.has_next_page = len(queryset) > self.page_size
        return queryset[:self.page_size]

    def get_paginated_response(self, data):
        # 信息流的系统 不太需要 'page_number', 'total_pages', 'total_results'
        return Response(data={
            'has_next_page': self.has_next_page,
            'results': data,
            # 当前页的数据
            # 1. tweets
            # 2. tweets = self.paginate_queryset(tweets)    分页
            # 3. serializer = TweetSerializer(instance=tweets, many=True, ...)
            # 4. return self.get_paginated_response(data=serializer.data)
        })