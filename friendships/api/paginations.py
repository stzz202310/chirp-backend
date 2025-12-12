from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class FriendshipPagination(PageNumberPagination):
    # 默认的 page size，也就是 page 没有在 url 参数里的时候
    page_size = 20
    # 默认的 page_size_query_param 是 None 表示不允许客户端指定每一页的大小
    # 如果加上这个配置，就表示客户端可以通过 size=10 来指定一个特定的大小用于不同的场景
    # 比如手机端和web端访问同一个API但是需要的 size 大小是不同的。
    # GET /api/friendships/1/followers/?size=10&page=3
    page_size_query_param = 'size'
    # 允许客户端指定的最大 max_page_size 是多少
    # 保护后端，防止客户一次请求过多的数据，对数据库造成压力，比如 page_size=10000
    max_page_size = 20
    # 第五页: Table.objects.all()[80:100] [(page_num - 1) * page_size : page_num * page_size]
    # A. SELECT * FROM `table` LIMIT 20 OFFSET 80
    # B. SELECT * FROM `table`  + return queryset[8:100]
    # 选 A; lazy loading, Table.objects.filter(...).filter(...) 会整合为一条 SQL 语句

    def get_paginated_response(self, data):
        # default: [count, next, previous, results]
        return Response(data={
            'total_results': self.page.paginator.count, # queryset.count()
            'total_pages': self.page.paginator.num_pages,
            'page_number': self.page.number,
            'has_next_page': self.page.has_next(),
            'results': data,
            # 当前页的数据
            # 1. friendships
            # 2. page = self.paginate_queryset(queryset=friendships)    分页
            # 3. serializer = FollowerSerializer(instance=page, many=True, ...)
            # 4. return self.get_paginated_response(data=serializer.data)
        })