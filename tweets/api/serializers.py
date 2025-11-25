from rest_framework import serializers

from accounts.api.serializers import UserSerializerForTweet
from comments.api.serializers import CommentSerializer
from likes.api.serializers import LikeSerializer
from likes.services import LikesService
from tweets.models import Tweet


class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet()
    # serializers.SerializerMethodField() ==> def get_XXX(self, obj | instance):
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField()
    # LikesService.has_liked ==> get_has_liked ==> has_liked => TweetSerializer 需要获取当前的 request.user
    # has_liked: 当前登陆用户request.user 是否赞过这个 tweet

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'created_at',
            'content',

            'comments_count',
            'likes_count',
            'has_liked',
        )

    def get_has_liked(self, obj):
        # self: serializer
        # obj: tweet
        return LikesService.has_liked(
            user=self.context['request'].user,
            target=obj,
        )

    def get_likes_count(self, obj):
        return obj.like_set.count()     # like_set 自定义

    def get_comments_count(self, obj):
        return obj.comment_set.count()  # comment_set django定义 [tweet as fk in `Comment`]


class TweetSerializerForDetail(TweetSerializer):
    # TweetSerializer: 精简版
    # TweetSerializerForDetail: 详细版 with Comments and Likes
    # TweetSerializerForDetail: 继承自 TweetSerializer，也需要获取当前的 request.user
    comments = CommentSerializer(source='comment_set', many=True)   # queryset = tweet.comment_set
    likes = LikeSerializer(source='like_set', many=True)

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'created_at',
            'content',

            'comments_count',
            'likes_count',
            'has_liked',

            'likes',
            'comments',
        )

    # # 2. 使用 serializers.SerializerMethodField 的方法实现 comments.
    # comments = serializers.SerializerMethodField()
    # def get_comments(self, obj):    # obj: tweet
    #     return CommentSerializer(obj.comment_set.all(), many=True).data


class TweetSerializerForCreate(serializers.ModelSerializer):
    content = serializers.CharField(min_length=6, max_length=140)

    class Meta:
        model = Tweet
        fields = ('content',)   # 发帖时, 只有 content 可以编辑|需要编辑

    def create(self, validated_data):
        user = self.context['request'].user # user = request.user
        content = validated_data.get('content')
        tweet = Tweet.objects.create(user=user, content=content)
        return tweet