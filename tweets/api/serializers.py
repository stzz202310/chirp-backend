from rest_framework import serializers
from tweets.models import Tweet
from accounts.api.serializers import UserSerializerForTweet

class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet()

    class Meta:
        model = Tweet
        fields = ('id', 'user', 'created_at', 'content',)


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