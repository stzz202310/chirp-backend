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
        # ModelSerializer: DRF 自动将 context 传递给嵌套 Serializer
        #   tweet = TweetSerializer()                       ← context 自动传入
        #   tweet = TweetSerializer(source='cached_tweet')  ← context 自动传入
        #
        # Serializer + SerializerMethodField: 无自动传递，需手动传入
        return TweetSerializer(instance=obj.cached_tweet, context=self.context).data

    def get_created_at(self, obj):
        return obj.created_at   # ⚠️ 直接返回 Python datetime 对象，没有经过 DRF DateTimeField 序列化

    def get_id(self, obj):
        return obj.id