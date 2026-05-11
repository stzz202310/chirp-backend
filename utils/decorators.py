from functools import wraps

from rest_framework import status
from rest_framework.response import Response


def required_params(method='GET', params=None):
    # print(1)
    if params is None:
        params = []

    def decorator(view_func):
        # print(2)
        """
        decorator 函数通过 wraps 来将 view_func 里的参数解析出来传递给 _wrapped_view
        这里的 instance 参数其实就是在 view_func 里的 self
                 def list(self,     request, *args, **kwargs):
        def _wrapped_view(instance, request, *args, **kwargs):
        """
        @wraps(view_func)
        def _wrapped_view(instance, request, *args, **kwargs):
            # print(3)
            if method.lower() == 'get':
                data = request.query_params
            else:
                data = request.data
            missing_params = [
                param
                for param in params
                if param not in data
            ]
            if missing_params:
                params_str = ', '.join(missing_params)
                return Response(data={
                    'message': 'missing {} in request'.format(params_str),
                    'success': False,
                }, status=status.HTTP_400_BAD_REQUEST)
            return view_func(instance, request, *args, **kwargs)
        return _wrapped_view
    return decorator

"""
1. 定义阶段(模块加载)
   decorator = required_params(method='GET', params=['user_id'])    执行 required_params(), 打印 1
   list = decorator(list)                                           执行 decorator(), 打印 2
   list = _wrapped_view                                             list 被替换为 _wrapped_view 函数对象   

2. 调用阶段(真正执行函数)
   list(instance, request) = _wrapped_view(instance, request)       打印 3

❌ 常见错误 return decorator(): Python 会直接执行 decorator()，但未传入 view_func，会报错
"""