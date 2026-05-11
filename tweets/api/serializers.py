from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForTweet
from comments.api.serializers import CommentSerializer
from likes.api.serializers import LikeSerializer
from likes.services import LikesService
from tweets.constants import TWEET_PHOTOS_UPLOAD_LIMIT
from tweets.models import Tweet
from tweets.services import TweetService
from utils.redis_helper import RedisHelper


class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet(source='cached_user')
    photo_urls = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField() # 当前用户是否点赞

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'created_at',
            'content',
            'photo_urls',

            'comments_count',
            'likes_count',
            'has_liked',
        )

    def get_has_liked(self, obj):
        return LikesService.has_liked(
            user=self.context['request'].user,
            target=obj,
        )

    def get_likes_count(self, obj):
        # TODO [Myself] cache.get_many(keys), 然后再处理 cache miss
        return RedisHelper.get_count(obj=obj, attr='likes_count')
        # return obj.like_set.count()       # like_set: 自定义; comment_set: django 定义
        # return obj.likes_count

    def get_comments_count(self, obj):
        return RedisHelper.get_count(obj=obj, attr='comments_count')

    def get_photo_urls(self, obj):
        photo_urls = []
        for photo in obj.tweetphoto_set.all().order_by('order'):
            photo_urls.append(photo.file.url)
        return photo_urls


class TweetSerializerForDetail(TweetSerializer):
    # comments = serializers.SerializerMethodField()    # 方法 1
    # def get_comments(self, obj):
    #     return CommentSerializer(instance=obj.comment_set.all(), many=True).data
    comments = CommentSerializer(source='comment_set', many=True)
    likes = LikeSerializer(source='like_set', many=True)

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'created_at',
            'content',
            'photo_urls',

            'comments_count',
            'likes_count',
            'has_liked',

            'likes',
            'comments',
        )


class TweetSerializerForCreate(serializers.ModelSerializer):
    content = serializers.CharField(min_length=6, max_length=140)
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=True,   # {'files': [list]} 检查 val: [list]  是否为空
        required=False,     # {'files': [list]} 检查 key: 'files' 是否存在
    )

    class Meta:
        model = Tweet
        fields = ('content', 'files')   # 发帖时, 只有 content 和 files [列表 list] 可以编辑

    def validate(self, data):
        if len(data.get('files', [])) > TWEET_PHOTOS_UPLOAD_LIMIT:
            raise ValidationError(detail={
                'message': f'You can upload {TWEET_PHOTOS_UPLOAD_LIMIT} photos at most'
            })
        return data

    def create(self, validated_data):   # 创建 tweet + tweetphoto
        user = self.context['request'].user
        content = validated_data.get('content')
        tweet = Tweet.objects.create(user=user, content=content)
        if validated_data.get('files'):
            TweetService.create_photos_from_files(
                tweet=tweet,
                files=validated_data.get('files'),
            )
        return tweet