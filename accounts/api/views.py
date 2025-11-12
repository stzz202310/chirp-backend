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
    queryset = User.objects.all()       # ModelViewSet 必需
    serializer_class = UserSerializer   # ModelViewSet 必需
    permission_classes = [permissions.IsAuthenticated]


class AccountViewSet(viewsets.ViewSet):
    serializer_class = SignupSerializer
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

    
    detail=True   单个对象    /api/accounts/{pk}/login_status/
    detail=False  列表       /api/accounts/login_status/
    request 代表“当前发起这次请求的用户”; 对作用于当前会话的动作 detail=False
    """
    @action(methods=['GET'], detail=False)
    def login_status(self, request):
    # @action(methods=['GET'], detail=True)
    # def login_status(self, request, pk):
        data = {
            'has_logged_in': request.user.is_authenticated,
            'ip': request.META.get('REMOTE_ADDR'),
        }
        if request.user.is_authenticated:
            data['user'] = UserSerializer(request.user).data
        return Response(data=data)

    @action(methods=['POST'], detail=False)
    def logout(self, request):
        django_logout(request)
        return Response(data={'success': True})

    @action(methods=['POST'], detail=False)
    def login(self, request):
        serializer = LoginSerializer(data=request.data) # get username and password from request
        if not serializer.is_valid():
            return Response(data={
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=400)

        username = serializer.validated_data.get('username')
        password = serializer.validated_data.get('password')

        # queryset = User.objects.filter(username=username)
        # print(queryset.query)
        # if not User.objects.filter(username=username).exists():
        #     return Response({
        #         "success": False,
        #         "message": "User does not exist.",
        #     }, status=400)

        user = django_authenticate(username=username, password=password)
        if not user or user.is_anonymous:
            return Response(data={
                "success": False,
                "message": "Username and password does not match.",
            }, status=400)

        django_login(request, user)
        return Response(data={
            "success": True,
            "user": UserSerializer(instance=user).data,
        })

    @action(methods=['POST'], detail=False)
    def signup(self, request):
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(data={
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=400)

        user = serializer.save()
        django_login(request, user)
        return Response(data={
            'success': True,
            'user': UserSerializer(instance=user).data,
        }, status=201)