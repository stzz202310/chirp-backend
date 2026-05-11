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

    @action(methods=['GET'], detail=False)
    @method_decorator(ratelimit(key='ip', rate='3/s', method='GET', block=True))
    def login_status(self, request):
        data = {
            'has_logged_in': request.user.is_authenticated,
            'ip': request.META['REMOTE_ADDR'],  # twitter.settings: INTERNAL_IPS = ['10.0.2.2',]
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
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(data={
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

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


class UserProfileViewSet(
    viewsets.GenericViewSet,
    viewsets.mixins.UpdateModelMixin,
):
    queryset = UserProfile
    serializer_class = UserProfileSerializerForUpdate
    permission_classes = (IsAuthenticated, IsObjectOwner,)  # AND