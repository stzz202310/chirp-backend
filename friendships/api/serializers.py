from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from accounts.api.serializers import UserSerializerForFriendship
from accounts.services import UserService
from friendships.services import FriendshipService


class BaseFriendshipSerializer(serializers.Serializer):
    # 某个用户的粉丝列表的某一行数据 FollowerSerializer : user = friendship_obj.from_user
    # 某个用户的关注列表的某一行数据 FollowingSerializer: user = friendship_obj.to_user
    user = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    # has_followed: 当前登陆用户[request.user] 是否已经关注 user
    has_followed = serializers.SerializerMethodField()
    """
    ⚠️ 为什么 Friendship / Newsfeed 适合使用 HBase 存储：
    1. 数据量大 (Newsfeed: 系统中数据量最大的表)
       - 传统关系型数据库在超大表下: 索引维护成本高, 扩展性受限
       - HBase 天然适合存储海量行数据

    2. 写多读少，且写入模式友好
       - 典型场景 Newsfeed
            一次读操作通常只对应一次数据读取
            一次写操作可能会触发多次 fanout 写入 (Push 模型的 fanout)
       - 该过程涉及大量顺序写入
       - HBase 对高吞吐写入（batch / 顺序写）非常友好

    3. 表结构简单(字段少、结构稳定), 查询需求有限
        Friendship 表: {字段 from_user, to_user, created_at}
        Newsfeed   表: {字段 user, tweet, created_at}
    
    ================================================================
    
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
       
    3. serializers.Serializer 需要手动实现的内容：
       - 字段定义 (fields = serializers.SerializerMethodField())
       - create() / update() 方法
       - 数据读写逻辑 [def create(): FriendshipService.follow(...)]
           
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


class FriendShipSerializerForCreate(serializers.Serializer):
    from_user_id = serializers.IntegerField()
    to_user_id = serializers.IntegerField()

    def validate(self, attrs):
        from_user_id = attrs.get('from_user_id')
        to_user_id = attrs.get('to_user_id')

        if from_user_id == to_user_id:
            raise ValidationError({'message': 'You can not follow yourself!'})

        if not User.objects.filter(id=to_user_id).exists(): # 重复检查
            raise ValidationError({'message': 'You can not follow a non-existent user!'})

        # if Friendship.objects.filter(from_user_id=from_user_id,to_user_id=to_user_id).exists():
        #     raise ValidationError({'message': 'You have already followed this user.'})

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