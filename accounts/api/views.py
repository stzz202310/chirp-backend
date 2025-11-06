from django.contrib.auth.models import User
from rest_framework import permissions
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import (
    login as django_login,
    logout as django_logout,
    authenticate as django_authenticate,
)

from accounts.api.serializers import (
    UserSerializer,
    LoginSerializer,
    SignupSerializer,
)

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


class AccountViewSet(viewsets.ViewSet):
    serializer_class = SignupSerializer
    """
    ModelViewSet：方便但暴露多，容易出现安全漏洞
    ViewSet：需要手动实现，但更安全、更灵活，推荐在涉及用户账户或敏感数据的接口使用

    | 特性          | `ModelViewSet`                               | `ViewSet`           |
    | ------------ | -------------------------------------------- | ------------------- |
    | 自动生成 CRUD | ✅（list, create, retrieve, update, destroy） | ❌ 需要自己手动实现方法             |
    | 自动关联模型  | ✅ 通过 `queryset` 和 `serializer_class`       | ❌ 没有自动绑定模型，需要自己处理数据 |
    | 灵活性       | 较低（自动暴露所有 CRUD）                        | 高（只暴露你想实现的接口）           |
    """

    """
    urls.py
    router = DefaultRouter()
    router.register(r'blogs', views.BlogViewSet)

    DRF 的 DefaultRouter 会帮你自动生成一系列 URL:
    | Action/Serializer Field | URL Name                              | URL Pattern            |
    | ----------------------- | ------------------------------------- | ---------------------- |
    | list                    | `blog-list`                           | `/blogs/`              |
    | retrieve                | `blog-detail`                         | `/blogs/<pk>/`         |
    | update / partial_update | `blog-update` / `blog-partial-update` | `/blogs/<pk>/`         |
    | destroy                 | `blog-destroy`                        | `/blogs/<pk>/`         |
    | custom action `content` | `blog-content`                        | `/blogs/<pk>/content/` |

    注意最后一行: 因为 BlogViewSet 里，我们定义了一个自定义 action
    DRF 会自动为这个 @action 生成一个 URL，并且默认命名规则是 <basename>-<action_name>
    
    basename  = accounts
    action    = login_status
    url name  = accounts-login_status
    
    DRF 不会把下划线自动转成连字符，URL name 保留下划线 (如果你愿意用 -，需要自己指定 url_path='login-status')
    
    | 写法                                              | URL Path                      | URL Name                |
    | ------------------------------------------------ | ----------------------------- | ----------------------- |
    | `@action(detail=False)`                          | `/api/accounts/login_status/` | `accounts-login_status` |
    | `@action(detail=False, url_path="login-status")` | `/api/accounts/login-status/` | `accounts-login-status` |

    """
    # detail=True   单个对象    /api/accounts/{pk}/login_status/
    # detail=False  列表       /api/accounts/login_status/
    # request 代表“当前发起这次请求的用户”; 对作用于当前会话的动作 detail=False

    @action(methods=['GET'], detail=False)
    def login_status(self, request):
    # @action(methods=['GET'], detail=True)
    # def login_status(self, request, pk):
        data = {'has_logged_in': request.user.is_authenticated}
        if request.user.is_authenticated:
            data['user'] = UserSerializer(request.user).data
        return Response(data)

    @action(methods=['POST'], detail=False)
    def logout(self, request):
        django_logout(request)
        return Response({'success': True})

    @action(methods=['POST'], detail=False)
    def login(self, request):
        # request = {
        #   "是谁发来的？"         → request.user
        #   "带来了什么数据？"      → request.data
        #   "URL 参数是什么？"     → request.query_params
        #   "是否登录？"           → request.user.is_authenticated
        # }
        # POST: request.data        参数位置: 请求体(HTTP Body)中, 而不是URL
        # GET: request.query_params 参数位置: URL末尾的问号之后
        serializer = LoginSerializer(data=request.data) # get username and password from request
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,    # You must call .is_valid() before accessing .errors
            }, status=400)

        # username = request.data.get('username')           # ❌原始请求数据, 未校验
        # username = serializer.validated_data['username']  # ✅serializer 校验后的数据; 会抛 KeyError
        username = serializer.validated_data.get('username')
        password = serializer.validated_data.get('password')

        # queryset = User.objects.filter(username=username)
        # print(queryset.query)
        if not User.objects.filter(username=username).exists():
            return Response({
                "success": False,
                "message": "User does not exist.",
            })

        user = django_authenticate(username=username, password=password)
        if not user or user.is_anonymous:
            return Response({
                "success": False,
                "message": "Username and password does not match.",
            }, status=400)

        django_login(request, user)
        return Response({
            "success": True,
            "user": UserSerializer(instance=user).data,
        })

    """
    在请求 login 前
    request.user = AnonymousUser
    request.data = 客户端发送的用户名和密码（未校验）
    request.user.is_authenticated = False

    调用 django_authenticate {检查用户名密码是否正确} + login {将 user 信息写入 session} 后:
    request.user = 已登录的 User 对象
    request.session 中保存了登录状态
    request.user.is_authenticated = True
    """

    @action(methods=['POST'], detail=False)
    def signup(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=400)

        user = serializer.save()
        django_login(request, user)
        return Response({
            'success': True,
            'user': UserSerializer(instance=user).data,
        }, status=201)