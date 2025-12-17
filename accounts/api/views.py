from django.contrib.auth import (
    login as django_login,
    logout as django_logout,
    authenticate as django_authenticate,
)
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response

from accounts.api.serializers import (
    UserSerializer,
    LoginSerializer,
    SignupSerializer,
    UserSerializerWithProfile,
    UserProfileSerializerForUpdate,
)
from accounts.models import UserProfile
from utils.permissions import IsObjectOwner


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()                   # ModelViewSet 必需
    serializer_class = UserSerializerWithProfile    # ModelViewSet 必需
    permission_classes = (IsAdminUser,)


class AccountViewSet(viewsets.ViewSet): # 登陆 注册
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

    
    detail=True   单个对象    /api/accounts/{pk}/login_status/  def login_status(self, request, pk):
    detail=False  列表       /api/accounts/login_status/       def login_status(self, request):
    request 代表“当前发起这次请求的用户”;
    """
    @action(methods=['GET'], detail=False)  # 作用于当前会话的动作: detail=False
    @method_decorator(ratelimit(key='ip', rate='3/s', method='GET', block=True))
    def login_status(self, request):
        # 查看用户当前的登录状态和具体信息
        data = {
            'has_logged_in': request.user.is_authenticated,
            'ip': request.META.get('REMOTE_ADDR'),
        }
        if request.user.is_authenticated:
            # request.user 已经在内存中了，不需要通过 缓存
            data['user'] = UserSerializer(instance=request.user).data
        return Response(data=data)

    @action(methods=['POST'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='POST', block=True))
    def logout(self, request):
        django_logout(request=request)
        return Response(data={'success': True})

    @action(methods=['POST'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='POST', block=True))
    def login(self, request):
        serializer = LoginSerializer(data=request.data) # get username and password from request
        if not serializer.is_valid():
            return Response(data={
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

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
            }, status=status.HTTP_400_BAD_REQUEST)

        django_login(request=request, user=user)
        return Response(data={
            "success": True,
            "user": UserSerializer(instance=user).data,
        }, status=status.HTTP_200_OK)

    @action(methods=['POST'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='POST', block=True))
    def signup(self, request):
        # 使用 username, email, password 进行注册
        serializer = SignupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(data={
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        django_login(request=request, user=user)
        return Response(data={
            'success': True,
            'user': UserSerializer(instance=user).data,
        }, status=status.HTTP_201_CREATED)


class UserProfileViewSet(   # 资料更新
    viewsets.GenericViewSet,
    viewsets.mixins.UpdateModelMixin,
):
    queryset = UserProfile
    permission_classes = (IsAuthenticated, IsObjectOwner,)
    serializer_class = UserProfileSerializerForUpdate