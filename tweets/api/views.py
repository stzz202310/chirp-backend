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
from utils.decorators import required_params


class TweetViewSet(viewsets.GenericViewSet):
    queryset = Tweet.objects.all()
    serializer_class = TweetSerializerForCreate

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]     # (): 实例化
        return [IsAuthenticated()]  # (): 实例化

    @required_params(method='GET', params=['user_id'])
    def list(self, request):    # GET /api/tweets/?user_id=1
        user_id = request.query_params.get('user_id')
        # 这句查询会被翻译为
        # select * from twitter_tweets
        # where user_id = xxx
        # order by created_at desc
        # 这句 SQL 查询会用到 user 和 created_at 的联合索引
        # 单纯的 user 索引是不够的
        tweets = Tweet.objects.filter(user_id=user_id).order_by('-created_at')

        # many = True, return list of dict
        # 1. if tweets 是一个 QuerySet
        # 2. if tweets 是一个模型对象列表 (如[tweet1, tweet2, tweet3])
        serializer = TweetSerializer(
            instance=tweets,
            many=True,
            context={'request': request},
        )
        # 一般来说 json 格式的 response 默认都要用 hash 的格式
        # 而不能用 list 的格式（约定俗成）
        return Response(data={'tweets': serializer.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, *args, **kwargs):
        # TODO [EASY]: 通过某个 query 参数 with_all_comments     来决定是否需要带上所有 comments
        # TODO [EASY]: 通过某个 query 参数 with_preview_comments 来决定是否需要带上前三条 comments
        tweet = self.get_object()
        serializer = TweetSerializerForDetail(
            instance=tweet,
            context={'request': request},
        )
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    def create(self, request):
        # 重载 create 方法，因为需要默认用当前登录用户作为 tweet.user
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
        tweet = serializer.save()   # save will call TweetSerializerForCreate.create()
        NewsFeedService.fanout_to_followers(tweet=tweet)
        return Response(
            data=TweetSerializer(instance=tweet, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )