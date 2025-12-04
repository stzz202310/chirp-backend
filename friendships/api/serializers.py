from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForFriendship
from friendships.models import Friendship
from friendships.services import FriendshipService


# 可以通过 source=xxx 指定去访问 model instance 的 xxx property
# 即 model_instance.xxx 来获得数据
class FollowerSerializer(serializers.ModelSerializer):      # 粉丝列表
    user = UserSerializerForFriendship(source='from_user')  # 类似 别名, from_user AS user
    # user = UserSerializerForFriendship(input -> friendship.from_user)
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed')

    def get_has_followed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        # TODO [HARD] 这个部分会对每个 object 都去执行一次 SQL 查询，速度会很慢，如何优化？
        return FriendshipService.has_followed(from_user=user, to_user=obj.from_user)


class FollowingSerializer(serializers.ModelSerializer): # 关注列表
    user = UserSerializerForFriendship(source='to_user')
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed',)

    def get_has_followed(self, obj):
        user = self.context['request'].user
        if user.is_anonymous:
            return False
        return FriendshipService.has_followed(from_user=user, to_user=obj.to_user)


class FriendShipSerializerForCreate(serializers.ModelSerializer):
    from_user_id = serializers.IntegerField()
    to_user_id = serializers.IntegerField()

    class Meta:
        model = Friendship
        fields = ('from_user_id', 'to_user_id',)

    def validate(self, attrs):
        from_user_id = attrs.get('from_user_id')
        to_user_id = attrs.get('to_user_id')

        if from_user_id == to_user_id:
            raise ValidationError({
                'message': 'You can not follow yourself!',
            })

        if not User.objects.filter(id=to_user_id).exists(): # 重复检查
            raise ValidationError({
                'message': 'You can not follow a non-existent user!',
            })

        if Friendship.objects.filter(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
        ).exists():
            raise ValidationError({
                'message': 'You have already followed this user.',
            })

        return attrs

    def create(self, validated_data):
        friendship = Friendship.objects.create(
            # Friendship.objects.create(from_user=user_obj)
            # Friendship.objects.create(from_user_id=1)
            from_user_id=validated_data['from_user_id'],
            to_user_id=validated_data['to_user_id'],
        )
        return friendship