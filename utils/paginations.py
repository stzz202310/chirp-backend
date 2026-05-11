from dateutil import parser
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from utils.time_constants import MAX_TIMESTAMP


class EndlessPagination(PageNumberPagination):
    page_size = 20 if not settings.TESTING else 10

    def __init__(self):
        # 可省略: PageNumberPagination, BasePagination 没有定义 __init__
        # super(EndlessPagination, self).__init__()

        # 增加一个实例属性 has_next_page
        self.has_next_page = False

    def to_html(self):  # 父类用于浏览器模式下渲染分页 HTML, 此处只需返回 JSON, 故不实现
        pass

    def paginate_queryset(self, queryset, request, view=None):
        # TODO [Homework] 优化"下拉刷新"
        if 'created_at__gt' in request.query_params:
            created_at__gt = request.query_params['created_at__gt']
            queryset = queryset.filter(created_at__gt=created_at__gt)
            self.has_next_page = False  # 所有最新数据，因此没有下一页
            return queryset.order_by('-created_at')

        if 'created_at__lt' in request.query_params:
            created_at__lt = request.query_params['created_at__lt']
            queryset = queryset.filter(created_at__lt=created_at__lt)

        # 请求没有带参数: 默认访问首页
        queryset = queryset.order_by('-created_at')[:self.page_size + 1]
        self.has_next_page = len(queryset) > self.page_size
        return queryset[:self.page_size]

    def paginate_hbase(self, hb_model, row_key_prefix, request):
        if 'created_at__gt' in request.query_params:
            created_at__gt = request.query_params['created_at__gt']
            start = (*row_key_prefix, created_at__gt)
            stop = (*row_key_prefix, MAX_TIMESTAMP)
            objects = hb_model.filter(start=start, stop=stop)
            if len(objects) and objects[0].created_at == int(created_at__gt):
                objects = objects[:0:-1]
            else:
                objects = objects[::-1]
            self.has_next_page = False
            return objects

        if 'created_at__lt' in request.query_params:
            created_at__lt = request.query_params['created_at__lt']
            start = (*row_key_prefix, created_at__lt)
            stop = (*row_key_prefix, None)
            objects = hb_model.filter(start=start, stop=stop, limit=self.page_size + 2, reverse=True)
            if len(objects) and objects[0].created_at == int(created_at__lt):
                # 如果第一条数据的 created_at 等于 created_at__lt, 则去掉第一条，避免重复返回
                objects = objects[1:]
            if len(objects) > self.page_size:
                self.has_next_page = True
                # objects = objects[:-1] 删除最后一条数据的旧方法，可能不够安全
                # 场景:
                #   - 第一条数据的 created_at != created_at__lt
                #   - 查询返回了 self.page_size + 2 条数据
                # 更安全的做法:
                #   - 直接截取前 self.page_size 条
                objects = objects[:self.page_size]
            else:
                self.has_next_page = False
            return objects

        # 请求没有带参数: 默认访问首页
        prefix = (*row_key_prefix, None)
        objects = hb_model.filter(prefix=prefix, limit=self.page_size + 1, reverse=True)
        if len(objects) > self.page_size:
            self.has_next_page = True
            objects = objects[:-1]
        else:
            self.has_next_page = False
        return objects

    def paginate_cached_list(self, cached_list, request):
        paginated_list = self.paginate_ordered_list(
            reverse_ordered_list=cached_list,
            request=request,
        )
        # 如果是向上翻页，paginated_list 里是所有的最新的数据，直接返回
        if 'created_at__gt' in request.query_params:
            return paginated_list
        # 如果还有下一页，说明 cached_list 里的数据还没有取完，也直接返回
        if self.has_next_page:
            return paginated_list
        # 如果 cached_list 的长度不足最大限制，说明 cached_list 里已经是所有数据了
        if len(cached_list) < settings.REDIS_LIST_LENGTH_LIMIT:
            return paginated_list
        # 如果进入这里，说明可能存在未加载到 cache 的数据，需要直接查询数据库
        return None

    def paginate_ordered_list(self, reverse_ordered_list, request):
        # reverse_ordered_list: 保存在 cache 中，一般不会太大，可以 for 循环
        # reverse_ordered_list: created_at 倒序排列 [.order_by('-created_at')]
        if 'created_at__gt' in request.query_params:
            # 兼容 iso格式[MySQL] 和 int格式[HBase] 两种时间格式
            # iso格式字符串: '2025-12-29T05:11:16.530588Z' → parser.isoparse() → datetime 对象
            # int格式字符串: '1767934515324687'            → int()             → int 时间戳
            # datetime 对象:  datetime(2025, 12, 29, 5, 11, 16, 530588, tzinfo=UTC) → .isoformat() → iso 格式字符串
            try:
                created_at__gt = parser.isoparse(request.query_params['created_at__gt'])
            except ValueError:
                created_at__gt = int(request.query_params['created_at__gt'])

            objects = []
            for obj in reverse_ordered_list:
                if obj.created_at > created_at__gt:
                    objects.append(obj)
                else:
                    break
            self.has_next_page = False
            return objects

        index = 0
        if 'created_at__lt' in request.query_params:
            try:
                created_at__lt = parser.isoparse(request.query_params['created_at__lt'])
            except ValueError:
                created_at__lt = int(request.query_params['created_at__lt'])

            for index, obj in enumerate(reverse_ordered_list):
                if obj.created_at < created_at__lt:
                    break
            else:
                # 没找到任何满足条件的 objects，返回空数组
                # 注意这个 else 对应的是 for
                reverse_ordered_list = []
        self.has_next_page = len(reverse_ordered_list) > index + self.page_size
        return reverse_ordered_list[index : index + self.page_size] # 左闭右开

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