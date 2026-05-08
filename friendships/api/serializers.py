from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForFriendship
from accounts.services import UserService
from friendships.services import FriendshipService


class BaseFriendshipSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    has_followed = serializers.SerializerMethodField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    def get_user_id(self, obj):
        raise NotImplementedError

    def _get_following_user_id_set(self):
        # 返回[当前登陆用户]的关注列表
        from_user = self.context['request'].user
        if from_user.is_anonymous:
            return {}
        if hasattr(self, '_cached_following_user_id_set'):
            return self._cached_following_user_id_set
        user_id_set = FriendshipService.get_following_user_id_set(
            from_user_id=from_user.id,
        )
        setattr(self, '_cached_following_user_id_set', user_id_set)
        return user_id_set

    def get_has_followed(self, obj):    # obj: friendship obj (⚠️ not user obj)
        return self.get_user_id(obj=obj) in self._get_following_user_id_set()

    def get_user(self, obj):
        user_id = self.get_user_id(obj=obj)
        user = UserService.get_user_by_id(user_id=user_id)
        return UserSerializerForFriendship(instance=user).data

    def get_created_at(self, obj):
        return obj.created_at


class FollowerSerializer(BaseFriendshipSerializer):
    # 粉丝列表 (to_user_id 的 followers)
    # {user=from_user_1} follow {to_user} at {created_at}, {当前用户 request.user} 是否 has_followed {user=from_user_1}
    # {user=from_user_2} follow {to_user} at {created_at}, {当前用户 request.user} 是否 has_followed {user=from_user_2}
    def get_user_id(self, obj):
        return obj.from_user_id


class FollowingSerializer(BaseFriendshipSerializer):
    # 关注列表 (from_user_id 的 followings)
    # {from_user} follow {user=to_user_1} at {created_at}, {当前用户 request.user} 是否 has_followed {user=to_user_1}
    # {from_user} follow {user=to_user_2} at {created_at}, {当前用户 request.user} 是否 has_followed {user=to_user_2}
    def get_user_id(self, obj):
        return obj.to_user_id


class FriendShipSerializerForCreate(serializers.Serializer):
    from_user_id = serializers.IntegerField()
    to_user_id = serializers.IntegerField()

    def validate(self, attrs):
        from_user_id = attrs.get('from_user_id')
        to_user_id = attrs.get('to_user_id')

        if from_user_id == to_user_id:
            raise ValidationError({'message': 'You can not follow yourself!'})

        if not User.objects.filter(id=to_user_id).exists(): # 重复检查 [self.get_object()]
            raise ValidationError({'message': 'You can not follow a non-existent user!'})

        return attrs

    def create(self, validated_data):
        from_user_id = validated_data['from_user_id']
        to_user_id = validated_data['to_user_id']
        friendship = FriendshipService.follow(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
        )
        return friendship

    def update(self, instance, validated_data):
        pass