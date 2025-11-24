from rest_framework import serializers

from accounts.api.serializers import UserSerializerForTweet
from comments.api.serializers import CommentSerializer
from tweets.models import Tweet


class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet()

    class Meta:
        model = Tweet
        fields = ('id', 'user', 'created_at', 'content',)


class TweetSerializerWithComments(TweetSerializer):
    comments = CommentSerializer(source='comment_set', many=True)
    # queryset = tweet.comment_set

    class Meta:
        model = Tweet
        fields = ('id', 'user', 'created_at', 'content', 'comments',)

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