from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class FriendshipPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'size'
    max_page_size = 20

    def get_paginated_response(self, data):
        # default: [count, next, previous, results]
        return Response(data={
            'total_results': self.page.paginator.count,     # 总记录数  queryset.count()
            'total_pages': self.page.paginator.num_pages,   # 总页数
            'page_number': self.page.number,                # 当前页码
            'has_next_page': self.page.has_next(),          # 是否有下一页
            'results': data,                                # 当前页数据
        })