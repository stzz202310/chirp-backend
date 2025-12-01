"""
URL configuration for twitter project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from debug_toolbar.toolbar import debug_toolbar_urls
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from accounts.api.views import UserViewSet, AccountViewSet
from comments.api.views import CommentViewSet
from friendships.api.views import FriendshipViewSet
from inbox.api.views import NotificationViewSet
from likes.api.views import LikeViewSet
from newsfeeds.api.views import NewsFeedViewSet
from tweets.api.views import TweetViewSet

# DRF提供的一个'自动路由器', 能自动根据ViewSet生成 标准RESTful风格的URL
router = routers.DefaultRouter()
# router.register(URL前缀 prefix, viewSet, [base_name])
# 告诉路由器: '我有一个视图集 UserViewSet, 请帮我生成以/api/users/开头的 URL 路由'
# /api/users/       base_name: 'XXX-list'   list, create
# /api/users/{pk}/  base_name: 'XXX-detail' retrieve, update/partial_update, destroy
router.register(r'api/users', UserViewSet)
router.register(r'api/accounts', AccountViewSet, basename='accounts')
router.register(r'api/tweets', TweetViewSet, basename='tweets')
router.register(r'api/friendships', FriendshipViewSet, basename='friendships')
router.register(r'api/newsfeeds', NewsFeedViewSet, basename='newsfeeds')
router.register(r'api/comments', CommentViewSet, basename='comments')
router.register(r'api/likes', LikeViewSet, basename='likes')
router.register(r'api/notifications', NotificationViewSet, basename='notifications')

urlpatterns = [
    path('admin/', admin.site.urls),
    # 把router 动生成的所有URL加入到 Django的总路由中; 这行代码等价于手动写出一堆 path (list, detail)
    path('', include(router.urls)),
    # 添加DRF提供的一个'登录/注销'界面 仅浏览器页面用到; 'api-auth/login/' 'api-auth/logout/'
    # 这样当你访问 /users/ 时, 页面右上角会出现 Login按钮
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
] + debug_toolbar_urls()
