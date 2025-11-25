from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForLike
from comments.models import Comment
from likes.models import Like
from tweets.models import Tweet


class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializerForLike()

    class Meta:
        model = Like
        fields = ('user', 'created_at') # 基于 comment | tweet 获得点赞信息


class BaseLikeSerializerForCreateAndCancel(serializers.ModelSerializer): # ✅继承
    # choices=['comment', 'tweet']: 用于前后端传输，并没有写在数据库中 (可以和前端约定，所以可以用字符串)
    content_type = serializers.ChoiceField(choices=['comment', 'tweet'])
    object_id = serializers.IntegerField()

    class Meta:
        model = Like
        fields = ('content_type', 'object_id',)

    def _get_model_class(self, data):
        # 这是一个内部方法（private-like），不建议在类外部调用
        if data['content_type'] == 'comment':
            return Comment
        if data['content_type'] == 'tweet':
            return Tweet
        return None

    def validate(self, data):
        model_class = self._get_model_class(data)
        if model_class is None:
            raise ValidationError({'content_type': 'Content type does not exist'})
        # if not model_class.objects.filter(id=data['object_id']).exists():
        # like_object = model_class.objects.get(id=data['object_id']) 如果get不到会直接报错5XX
        like_object = model_class.objects.filter(id=data['object_id']).first()
        if like_object is None: # 报错4XX
            raise ValidationError({'object_id': 'Object does not exist'})
        return data


class LikeSerializerForCreate(BaseLikeSerializerForCreateAndCancel):

    def create(self, validated_data):
        model_class = self._get_model_class(validated_data)
        instance, _ = Like.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(model_class),
            object_id=validated_data['object_id'],
            user = self.context['request'].user,
        )
        return instance


class LikeSerializerForCancel(BaseLikeSerializerForCreateAndCancel):

    def cancel(self):
        """
        cancel 方法是一个自定义的方法，cancel 不会被 serializer.save() 调用
        所以需要直接调用 serializer.cancel()
        """
        model_class = self._get_model_class(self.validated_data)
        deleted, rows_count = Like.objects.filter(
            content_type=ContentType.objects.get_for_model(model_class),
            object_id=self.validated_data['object_id'],
            user=self.context['request'].user,
        ).delete()  # 即便这个赞不存在，也不会报错
        return deleted, rows_count