from debug_toolbar.toolbar import debug_toolbar_urls
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from accounts.api.views import UserViewSet, AccountViewSet, UserProfileViewSet
from comments.api.views import CommentViewSet
from friendships.api.views import FriendshipViewSet
from inbox.api.views import NotificationViewSet
from likes.api.views import LikeViewSet
from newsfeeds.api.views import NewsFeedViewSet
from tweets.api.views import TweetViewSet

router = routers.DefaultRouter()

router.register(r'api/users', UserViewSet, basename='users')
router.register(r'api/accounts', AccountViewSet, basename='accounts')
router.register(r'api/tweets', TweetViewSet, basename='tweets')
router.register(r'api/friendships', FriendshipViewSet, basename='friendships')
router.register(r'api/newsfeeds', NewsFeedViewSet, basename='newsfeeds')
router.register(r'api/comments', CommentViewSet, basename='comments')
router.register(r'api/likes', LikeViewSet, basename='likes')
router.register(r'api/notifications', NotificationViewSet, basename='notifications')
router.register(r'api/profiles', UserProfileViewSet, basename='profiles')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
] + debug_toolbar_urls()