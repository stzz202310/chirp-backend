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
    # serializers.SerializerMethodField() ==> def get_XXX(self, obj | instance):
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField()
    # LikesService.has_liked ==> get_has_liked ==> has_liked => TweetSerializer 需要获取当前的 request.user
    # has_liked: 当前登陆用户request.user 是否赞过这个 tweet
    photo_urls = serializers.SerializerMethodField()

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
        # self: serializer
        # obj: tweet
        return LikesService.has_liked(
            user=self.context['request'].user,
            target=obj,
        )

    def get_likes_count(self, obj):
        # if random.randint(0, 1000) == 0:  # [左闭右闭]
        #     likes_count = obj.like_set.count()
        #     if obj.likes_count != likes_count:
        #         obj.likes_count = likes_count
        #         obj.save()
        #     return likes_count
        # return obj.likes_count
        """ 
        Like  Table: return obj.like_set.count()    
        Tweet Table: return obj.likes_count
        
        Single Source of Truth (SSOT)
        Multi Sources of Truth (MSOT): 数据不一致
        1. ignore: 数据不敏感，准确性不重要
        2. Timeout: 定时从数据库回填
        
        GET /api/tweets/1/ => response.data['likes_count'] 
        ✅ def get_likes_count() 
        ❌ 模型字段 tweet.likes_count
        
        obj.likes_count = likes_count;  obj.save()   ❌ 不需要 obj.refresh_from_db()
        Tweet.objects.filter(...).update(...)        ✅ 需要 obj.refresh_from_db()
        """
        # N + 1 Queries: select count(*) -> redis get
        # ❌ N 如果是 db queries
        # ✅ N 如果是 cache queries
        # TODO [Myself] cache.get_many(keys), 然后再处理 cache miss
        return RedisHelper.get_count(obj=obj, attr='likes_count')
        # return obj.like_set.count()   # like_set 自定义
        # return obj.likes_count

    def get_comments_count(self, obj):
        return RedisHelper.get_count(obj=obj, attr='comments_count')
        # return obj.comment_set.count()  # comment_set django定义 [tweet as fk in `Comment`]
        # return obj.comments_count

    def get_photo_urls(self, obj):
        photo_urls = []
        for photo in obj.tweetphoto_set.all().order_by('order'):
            photo_urls.append(photo.file.url)
        return photo_urls


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
            'photo_urls',

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
    files = serializers.ListField(
        child=serializers.FileField(),
        allow_empty=True,   # {'files': [list]} 检查 val: [list]  是否为空
        required=False,     # {'files': [list]} 检查 key: 'files' 是否存在
        # max_length, min_length
    )

    class Meta:
        model = Tweet
        fields = ('content', 'files')   # 发帖时, 只有 content 和 files [列表 list] 可以编辑|需要编辑

    def validate(self, data):
        if len(data.get('files', [])) > TWEET_PHOTOS_UPLOAD_LIMIT:
            raise ValidationError(detail={
                'message': f'You can upload {TWEET_PHOTOS_UPLOAD_LIMIT} photos '
                            'at most'
            })
        return data

    def create(self, validated_data):
        user = self.context['request'].user # user = request.user
        content = validated_data.get('content')
        tweet = Tweet.objects.create(user=user, content=content)
        if validated_data.get('files'):
            TweetService.create_photos_from_files(
                tweet=tweet,
                files=validated_data.get('files'),
            )
        return tweet