from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForFriendship
from friendships.models import Friendship


# 可以通过 source=xxx 指定去访问 model instance 的 xxx property
# 即 model_instance.xxx 来获得数据
class FollowerSerializer(serializers.ModelSerializer):  # 粉丝列表
    user = UserSerializerForFriendship(source='from_user')
    # user = UserSerializerForFriendship(input -> friendship.from_user)

    class Meta:
        model = Friendship
        fields = ('user', 'created_at')


class FollowingSerializer(serializers.ModelSerializer):
    user = UserSerializerForFriendship(source='to_user')

    class Meta:
        model = Friendship
        fields = ('user', 'created_at')


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
            from_user_id=validated_data['from_user_id'],
            to_user_id=validated_data['to_user_id'],
        )
        return friendship