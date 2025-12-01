from functools import wraps

from rest_framework import status
from rest_framework.response import Response


def required_params(method='GET', params=None):
    """
    当我们使用 @required_params(method='GET', params=['some_params']) 的时候
    这个 required_params 函数应该需要返回一个 decorator 函数,
    这个 decorator 函数的参数 就是被 @required_params 包裹起来的函数 view_func
    """

    # 从效果上来说，参数中写 params=[] 很多时候也没有太大的问题
    # 但是从好的编程习惯上来说，函数的参数列表中的值不能是一个 mutable 的参数
    if params is None:
        params = []

    def decorator(view_func):   # views.py 中的 function
        """
        decorator 函数通过 wraps 来将 view_func 里的参数解析出来传递给 _wrapped_view
        这里的 instance 参数其实就是在 view_func 里的 self
                 def list(self,     request, *args, **kwargs):
        def _wrapped_view(instance, request, *args, **kwargs):
        """
        @wraps(view_func)
        def _wrapped_view(instance, request, *args, **kwargs):
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
            # 做完检测之后，再去调用 @required_params 包裹起来的 view_func
            return view_func(instance, request, *args, **kwargs)
        return _wrapped_view

    # 返回的是 一个 decorator 函数
    # 这个 decorator 等待被 Python 用 @ 语法传入 view_func [view_func 最终被替换成 _wrapped_view]
    return decorator    # return decorator() Python 会直接执行 decorator()，但是你还没传 view_func 进去 [❌报错]

"""

不带参数的装饰器 两层  view_func = (decorator 函数)(view_func)
带参数的装饰器   三层  view_func = (required_params(method='GET', params=None))(view_func)
1. 最外层 参数              def required_params(method='GET', params=None)
2. 中间层 被装饰函数         def decorator(view_func)
3. 最内层 被装饰函数的参数    def _wrapped_view(view_func 的参数)

def required_params(method='GET', params=None):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(instance, request, *args, **kwargs):
            # 检查 是否有 missing_params
            return view_func(instance, request, *args, **kwargs)
        return _wrapped_view
    return decorator

"""