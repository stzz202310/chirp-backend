from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForComment
from comments.models import Comment
from likes.services import LikesService
from tweets.models import Tweet


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializerForComment(source='cached_user')
    # has_liked: 当前登陆用户 request.user 是否赞过这个 comment
    has_liked = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = (
            'id',
            'tweet_id',
            'user',
            'content',
            'created_at',
            'updated_at',

            'has_liked',
            'likes_count',
        )

    def get_has_liked(self, obj):
        return LikesService.has_liked(
            user=self.context['request'].user,
            target=obj,
        )

    def get_likes_count(self, obj):
        return obj.like_set.count()


class CommentSerializerForCreate(serializers.ModelSerializer):
    # 需要手动添加 tweet_id 和 user_id
    # 因为 ModelSerializer 默认只会包含模型字段 (tweet, user)
    tweet_id = serializers.IntegerField()
    user_id = serializers.IntegerField()

    class Meta:
        model = Comment
        fields = ('content', 'tweet_id', 'user_id',)

    def validate(self, attrs):
        tweet_id = attrs['tweet_id']
        if not Tweet.objects.filter(id=tweet_id).exists():
            raise ValidationError({'message': 'Tweet does not exist.'})
        return attrs

class CommentSerializerForUpdate(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('content',)

    def update(self, instance, validated_data):
        instance.content = validated_data.get('content')
        instance.save()
        return instance