from rest_framework import serializers

from newsfeeds.models import NewsFeed
from tweets.api.serializers import TweetSerializer


class NewsFeedSerializer(serializers.ModelSerializer):
    tweet = TweetSerializer(source='cached_tweet') # has_liked: 需要获取当前的 request.user

    class Meta:
        model = NewsFeed
        fields = ('id', 'created_at', 'tweet')