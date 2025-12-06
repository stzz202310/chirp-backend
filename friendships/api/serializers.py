from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForFriendship
from friendships.models import Friendship
from friendships.services import FriendshipService


class FollowingUserIdSetMixin: # mixin: 插件

    @property
    def following_user_id_set(self: serializers.ModelSerializer):
        # [http request -> web服务器 -> http response]
        # instance|object 级别的缓存: 进程结束，缓存就会被释放
        if self.context.get('request').user.is_anonymous:
            return {}
        if hasattr(self, '_cached_following_user_id_set'):
            return self._cached_following_user_id_set
        user_id_set = FriendshipService.get_following_user_id_set(
            from_user_id=self.context['request'].user.id,
        )
        setattr(self, '_cached_following_user_id_set', user_id_set)
        return user_id_set


class FollowerSerializer(serializers.ModelSerializer, FollowingUserIdSetMixin): # 粉丝列表
    user = UserSerializerForFriendship(source='cached_from_user')
    # user = UserSerializerForFriendship(input -> friendship.from_user)
    # 可以通过 source=xxx 指定去访问 model instance 的 xxx property
    # 即 model_instance.xxx 来获得数据
    # https://www.django-rest-framework.org/api-guide/serializers/#specifying-fields-explicitly
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed')

    def get_has_followed(self, obj):
        return obj.from_user_id in self.following_user_id_set


class FollowingSerializer(serializers.ModelSerializer, FollowingUserIdSetMixin): # 关注列表
    user = UserSerializerForFriendship(source='cached_to_user')
    has_followed = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = ('user', 'created_at', 'has_followed',)

    def get_has_followed(self, obj):
        return obj.to_user_id in self.following_user_id_set


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