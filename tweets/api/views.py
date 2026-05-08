from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from newsfeeds.services import NewsFeedService
from tweets.api.serializers import (
    TweetSerializer,
    TweetSerializerForDetail,
    TweetSerializerForCreate,
)
from tweets.models import Tweet
from tweets.services import TweetService
from utils.decorators import required_params
from utils.paginations import EndlessPagination


class TweetViewSet(viewsets.GenericViewSet):
    queryset = Tweet.objects.all()
    serializer_class = TweetSerializerForCreate
    pagination_class = EndlessPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()] # key='user_or_ip'
        return [IsAuthenticated()]

    @required_params(method='GET', params=['user_id'])
    @method_decorator(ratelimit(key='user_or_ip', rate='5/s', method='GET', block=True))
    def list(self, request):
        user_id = request.query_params.get('user_id')
        cached_tweets = TweetService.get_cached_tweets(user_id=user_id)
        page = self.paginator.paginate_cached_list(
            cached_list=cached_tweets,
            request=request,
        )
        if page is None:
            # queryset = Tweet.objects.filter(...)
            queryset = self.queryset.filter(user_id=user_id)\
                .prefetch_related('user')\
                .order_by('-created_at')

            # def paginate_queryset(self, queryset):
            #    return self.paginator.paginate_queryset(queryset, self.request, view=self)
            page = self.paginate_queryset(queryset=queryset)

        serializer = TweetSerializer(
            instance=page,
            many=True,
            context={'request': request},
        )   # many = True, return list of dict
        return self.get_paginated_response(data=serializer.data)

    @method_decorator(ratelimit(key='user_or_ip', rate='5/s', method='GET', block=True))
    def retrieve(self, request, *args, **kwargs):
        tweet = self.get_object()
        # tweet = MemcachedHelper.get_object_through_cache(
        #     model_class=Tweet,
        #     object_id=int(kwargs.get('pk')),
        # )
        serializer = TweetSerializerForDetail(
            instance=tweet,
            context={'request': request},
        )
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @method_decorator(ratelimit(key='user', rate='1/s', method='POST', block=True))
    @method_decorator(ratelimit(key='user', rate='5/m', method='POST', block=True))
    def create(self, request):
        serializer = TweetSerializerForCreate(
            data=request.data,
            context={'request': request},
        )

        if not serializer.is_valid():
            return Response(data={
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        tweet = serializer.save()
        NewsFeedService.fanout_to_followers(tweet=tweet)
        return Response(
            data=TweetSerializer(instance=tweet, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )