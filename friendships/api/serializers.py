from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForFriendship
from accounts.services import UserService
from friendships.models import Friendship
from friendships.services import FriendshipService


class BaseFriendshipSerializer(serializers.Serializer):
    user = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    has_followed = serializers.SerializerMethodField()
    """
    Friendship 表: {字段 from_user, to_user, created_at}
    Newsfeed   表: {字段 user, tweet, created_at}
    结构简单 写多读少[例如: fanout(给用户的所有 followers 推送数据)], 适合使用 HBase 进行存储
    
    一 数据库迁移：MySQL -> HBase
       - 在不中断线上服务的前提下完成数据库迁移
       - 支持新老数据库并存 + 灰度切换
    
    二 兼容方案 (核心设计)
    1. 同时兼容 hbase_models.py 和 Django ORM models.py（以 Friendship 为例）
       - 通过 GateKeeper 控制使用哪一种数据源
            percent = 0%    -> 全量走 MySQL（旧逻辑）
            percent = 100%  -> 全量走 HBase（新逻辑）
    
    2. 不再直接依赖 Django ORM
       - 不能继续使用 serializers.ModelSerializer 绑定 models.py
       - 改为使用 serializers.Serializer，与 ORM 解耦
       
    3. serializers.Serializer 需要手动实现：
       - 字段定义 (fields = serializers.SerializerMethodField())
       - create() / update() 方法
       - 数据读写逻辑 [def create(): FriendshipService.follow(...)]

    三 设计取舍说明
    - serializers.ModelSerializer：
        - 优点：自动生成字段和 CRUD，开发成本低
        - 缺点：强依赖 Django ORM，不利于多数据库兼容
    
    - serializers.Serializer + SerializerMethodField：
        - 优点：更灵活，可同时支持 MySQL / HBase
        - 缺点：需要手动实现更多逻辑，代码更“裸露”
    """

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        # BaseFriendshipSerializer 仅用于 [返回给客户端的展示数据], 不负责数据创建
        # 负责定义 response 中允许暴露的 fields
        #
        # create / update 等写操作：
        # - 不定义在 BaseFriendshipSerializer 中
        # - 而是放在专门的写入 Serializer（如 FriendshipSerializerForCreate）
        #
        # 这样做的目的：
        # 1. 分离读写职责，返回字段与写入字段解耦，避免误用
        # 2. 防止敏感字段被意外暴露（数据安全）
        # 3. 便于同时支持 MySQL / HBase 等不同存储实现
        pass

    def get_user_id(self, obj):
        # FollowerSerializer : return obj.from_user_id
        # FollowingSerializer: return obj.to_user_id
        raise NotImplementedError

    def _get_following_user_id_set(self):
        # 返回[当前登陆用户]的关注列表
        from_user = self.context['request'].user
        if from_user.is_anonymous:
            return {}
        if hasattr(self, '_cached_following_user_id_set'):
            # [http request -> web服务器 -> http response]
            # instance|object 级别的缓存: 进程结束，缓存就会被释放
            return self._cached_following_user_id_set
        user_id_set = FriendshipService.get_following_user_id_set(
            from_user_id=from_user.id,
        )
        setattr(self, '_cached_following_user_id_set', user_id_set)
        return user_id_set

    def get_has_followed(self, obj):    # obj: friendship obj
        return self.get_user_id(obj=obj) in self._get_following_user_id_set()

    def get_user(self, obj):
        user_id = self.get_user_id(obj=obj)
        user = UserService.get_user_by_id(user_id=user_id)
        # ⚠️ return .data
        return UserSerializerForFriendship(instance=user).data

    def get_created_at(self, obj):
        return obj.created_at


class FollowerSerializer(BaseFriendshipSerializer): # 粉丝列表
    def get_user_id(self, obj):
        return obj.from_user_id


class FollowingSerializer(BaseFriendshipSerializer): # 关注列表
    def get_user_id(self, obj):
        return obj.to_user_id


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
        from_user_id = validated_data['from_user_id']
        to_user_id = validated_data['to_user_id']
        friendship = FriendshipService.follow(
            from_user_id=from_user_id,
            to_user_id=to_user_id,
        )
        return friendship