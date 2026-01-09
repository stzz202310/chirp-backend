from rest_framework import serializers

from tweets.api.serializers import TweetSerializer


class NewsFeedSerializer(serializers.Serializer):
    # has_liked: 需要获取当前的 request.user
    # class NewsFeedSerializer(serializers.ModelSerializer):
    #   tweet = TweetSerializer(source='cached_tweet')
    #   1. DRF 会自动把 self.context 传给嵌套的 TweetSerializer, 不需要手动传 context
    tweet = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def get_tweet(self, obj):
        # 2. SerializerMethodField 只是调用方法，没有自动 context 传递机制
        #    必须手动把 context=self.context 传给嵌套 Serializer
        return TweetSerializer(instance=obj.cached_tweet, context=self.context).data

    def get_created_at(self, obj):
        return obj.created_at

    def get_id(self, obj):
        return obj.id