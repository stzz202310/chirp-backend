from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from newsfeeds.services import NewsFeedService
from tweets.api.serializers import TweetSerializer, TweetSerializerForCreate
from tweets.models import Tweet


class TweetViewSet(viewsets.GenericViewSet):
    # queryset = Tweet.objects.all()
    serializer_class = TweetSerializerForCreate

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]     # (): 实例化
        return [IsAuthenticated()]  # (): 实例化

    def list(self, request):    # GET /api/tweets/?user_id=1
        if 'user_id' not in request.query_params:
            return Response(data={'Missing user_id'}, status=400)
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
        serializer = TweetSerializer(instance=tweets, many=True)
        # 一般来说 json 格式的 response 默认都要用 hash 的格式
        # 而不能用 list 的格式（约定俗成）
        return Response(data={'tweets': serializer.data}, status=200)

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
            }, status=400)
        tweet = serializer.save()   # save will call TweetSerializerForCreate.create()
        NewsFeedService.fanout_to_followers(tweet=tweet)
        return Response(data=TweetSerializer(instance=tweet).data, status=201)