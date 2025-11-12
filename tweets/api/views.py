from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from tweets.models import Tweet
from tweets.api.serializers import TweetSerializer, TweetSerializerForCreate


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
        tweets = Tweet.objects.filter(user_id=user_id).order_by('-created_at')

        # many = True, return list of dict
        # 1. if tweets 是一个 QuerySet
        # 2. if tweets 是一个模型对象列表 (如[tweet1, tweet2, tweet3])
        serializer = TweetSerializer(instance=tweets, many=True)
        return Response(data={'tweets': serializer.data}, status=200)

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
            }, status=400)
        tweet = serializer.save()   # save will call TweetSerializerForCreate.create()
        return Response(data=TweetSerializer(tweet).data, status=201)