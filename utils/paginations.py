from dateutil import parser
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from utils.time_constants import MAX_TIMESTAMP


class EndlessPagination(PageNumberPagination):
    page_size = 20 if not settings.TESTING else 10

    def __init__(self):
        # 调用父类构造函数，维持 DRF 的正常逻辑
        # 可省略: PageNumberPagination, BasePagination 没有定义 __init__
        # super(EndlessPagination, self).__init__()
        self.has_next_page = False  # 增加一个实例属性 has_next_page

    def to_html(self):  # 用于 浏览器模式下分页 HTML 展示 [但现实里 DRF 很少用它]
        pass            # 不需要 HTML 输出, 只输出 JSON

    def paginate_queryset(self, queryset, request, view=None):
        """""""""
        Endless Pagination
        如何不依赖于 中心化的数据库节点，实现一个分布式的全局递增的 ID生成算法？
        中心化的数据库节点: 由中心统一分配 [加锁, 获取当前最大id => id+1 => 更新回数据库, 解锁 => 分配此id]

        ✅ snowflake:  unique, 有序自增，但是不连续 TODO [HARD]
        ✅ created_at: unique, 有序自增，但是不连续 [活跃用户 < 100M]
        ❌ uuid:       unique, 无序，不连续
        """
        if 'created_at__gt' in request.query_params:
            # [顶部]下拉刷新 Pull-to-Refresh
            # created_at__gt 用于下拉刷新的时候加载[所有]最新的内容进来
            # 为了简单起见，下拉刷新不做翻页机制，直接加载所有更新的数据
            # 因为如果数据很久没有更新的话，不会采用下拉刷新的方式进行更新，而是重新加载最新的数据
            # TODO [HARD] 三年后刷新，新帖子太多: 仅显示最新的20条, 并且不要和[之前的帖子]拼到一起
            # TODO [HARD] 如何处理翻页结果中的无权限内容? [白名单|黑名单|已删除的帖子: cache 方便查找]
            #   先queryset，再筛选: 如果直接通过 queryset 筛选，效率会非常低
            #   例子: 用户A 查看 用户B的帖子 page_size=3
            #   第一次得到 帖子[9, 8, 7], 用户A没有权限看9
            #   第二次得到 帖子[6, 5, 4], 用户A没有权限看4
            #   返回 [9, 8, 6]
            created_at__gt = request.query_params['created_at__gt']
            queryset = queryset.filter(created_at__gt=created_at__gt)
            self.has_next_page = False  # 所有最新数据，因此没有下一页
            return queryset.order_by('-created_at')

        if 'created_at__lt' in request.query_params:
            # [底部]上拉加载更多 Load More
            # created_at__lt 用于向上滚屏 (往下翻页) 的时候加载下一页的数据(旧数据)
            # 寻找 created_at < created_at__lt 的 objects 里按照 created_at 倒序的
            # 前 page_size + 1 个 objects
            # 比如目前的 created_at 列表是 [10, 9, 8, 7, ... 1] (⚠️ MySQL 和 HBase 的 ordering)
            # 如果 created_at__lt=10, page_size=2 则应该返回 [9, 8, 7],
            # 多返回一个 object 是为了判断是否还有下一页从而减少一次空加载|空刷
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
                # [start:stop:step] [start, stop)
                # [1, 2, 3] => [3, 2]
                objects = objects[:0:-1]
            else:
                objects = objects[::-1]
            self.has_next_page = False
            return objects

        if 'created_at__lt' in request.query_params:
            created_at__lt = request.query_params['created_at__lt']
            start = (*row_key_prefix, created_at__lt)
            stop = (*row_key_prefix, None)
            """
            1. limit = self.page_size + 2:
                HBase 仅支持 <= created_at__lt 的查询条件, 不支持严格的小于(< created_at__lt)
                (<= created_at__lt, limit=page_size+2) 等价于 (< created_at__lt, limit=page_size+1)
            
            2. HBase RowKey 为字符串字典序 (timestamp 从小到大)
               若需要按 created_at 倒序('-created_at'), 需设置
                a. objects = hb_model.filter(reverse=True)
                b. objects = hb_model.filter(), objects = objects[::-1]
            
            3. HBase scan 范围查询 [start, stop)
               示例 RowKey(user_id, created_at) 顺序：
                  (1, ts1)
                  (2, None) -> stop 必须在这里停止，否则会扫描到用户1的数据
                  (2, ts1)  
                  (2, ts2)  -> start
                  (2, Max)
                
                - 正确设置 stop 可以避免越界读取其他用户的数据
                - 可灵活使用 (1, None) 或 (1, 999999) 作为界限
            """
            objects = hb_model.filter(start=start, stop=stop, limit=self.page_size + 2, reverse=True)
            if len(objects) and objects[0].created_at == int(created_at__lt):
                # 如果第一条数据的 created_at 等于 created_at__lt, 则去掉第一条，避免重复返回
                objects = objects[1:]
            if len(objects) > self.page_size:
                self.has_next_page = True
                # objects = objects[:-1]
                # 删除最后一条数据的旧方法，可能不够安全
                # 场景：
                #   - 第一条数据的 created_at != created_at__lt
                #   - 查询返回了 self.page_size + 2 条数据
                # 更安全的做法：
                #   - 直接截取前 self.page_size 条
                objects = objects[:self.page_size]
            else:
                self.has_next_page = False
            return objects

        # 没有任何参数，默认加载最新的一页
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
        # 如果进入这里，说明可能存在[数据库里没有 load 在 cache 里的数据], 需要直接去数据库查询
        return None

    def paginate_ordered_list(self, reverse_ordered_list, request):
        # reverse_ordered_list: 保存在 cache 中，一般不会太大，可以 for 循环
        # reverse_ordered_list: created_at 倒序排列 [.order_by('-created_at')]
        if 'created_at__gt' in request.query_params:
            created_at__gt = parser.isoparse(request.query_params['created_at__gt'])
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
            created_at__lt = parser.isoparse(request.query_params['created_at__lt'])
            for index, obj in enumerate(reverse_ordered_list):
                if obj.created_at < created_at__lt:
                    break
            else:
                # 没找到任何满足条件的 objects，返回空数组
                # 注意这个 else 对应的是 for

                # lst = []
                # lst[10]      ❌ IndexError
                # lst[10:20]   ✅ 返回 []
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