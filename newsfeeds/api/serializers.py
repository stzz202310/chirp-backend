from rest_framework import serializers

from tweets.api.serializers import TweetSerializer


class NewsFeedSerializer(serializers.Serializer):
    tweet = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def get_tweet(self, obj):
        return TweetSerializer(instance=obj.cached_tweet, context=self.context).data

    def get_created_at(self, obj):
        return obj.created_at   # ⚠️ 直接返回 Python datetime 对象，没有经过 DRF DateTimeField 序列化

    def get_id(self, obj):
        return obj.id