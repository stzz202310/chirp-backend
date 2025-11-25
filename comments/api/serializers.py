from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForComment
from comments.models import Comment
from likes.services import LikesService
from tweets.models import Tweet


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializerForComment()
    has_liked = serializers.SerializerMethodField() # 当前登陆用户request.user 是否赞过这个 comment
    likes_count = serializers.SerializerMethodField()
    # TODO: CommentSerializerForDetail
    # likes = LikeSerializer(source='like_set', many=True)

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
    # 这两项必须手动添加
    # 因为默认 ModelSerializer 里只会自动包含 user 和 tweet 而不是 user_id 和 tweet_id
    tweet_id = serializers.IntegerField()
    user_id = serializers.IntegerField()

    class Meta:
        model = Comment
        fields = ('content', 'tweet_id', 'user_id',)

    def validate(self, attrs):
        tweet_id = attrs.get('tweet_id')
        if not Tweet.objects.filter(id=tweet_id).exists():
            raise ValidationError({'message': 'Tweet does not exist.'})
        # 必须 return validated data
        # 也就是验证过之后，进行过处理的输入数据 [当然，也可以是不做处理的数据]
        return attrs

class CommentSerializerForUpdate(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('content',)   # update: 只能修改 content

    def update(self, instance, validated_data):
        instance.content = validated_data.get('content')
        instance.save()
        # update 方法要求 return 修改后的 instance 作为返回值
        return instance
