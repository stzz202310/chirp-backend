from django.conf import settings

from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer


class RedisHelper:

    @classmethod
    def _load_objects_to_cache(cls, key, objects):
        conn = RedisClient.get_connection()

        serialized_list = []
        for obj in objects:
            serialized_data = DjangoModelSerializer.serialize(instance=obj)
            serialized_list.append(serialized_data)

        if serialized_list:
            """
            rpush: {key: [list类型 | 列表, 和 queryset 顺序一致]}
            
            conn.rpush(key, 1)
            conn.rpush(key, 2)
            conn.rpush(key, 3)          ❌ [N + 1]rpush: [N + 1]次网络请求
            conn.rpush(key, 1, 2, 3)    ✅ 1 rpush
            conn.rpush(key, *[1, 2, 3])   *serialized_list: 一个一个放进去 
            """
            conn.rpush(key, *serialized_list)
            conn.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)

    @classmethod
    def load_objects(cls, key, queryset):   # 读
        conn = RedisClient.get_connection()

        # cache hit: 直接拿出来，然后返回
        if conn.exists(key):
            # [左闭右闭，从左向右全部取出来]
            serialized_list = conn.lrange(name=key, start=0, end=-1)
            objects = []
            for serialized_data in serialized_list:
                deserialized_obj = DjangoModelSerializer.deserialize(serialized_data=serialized_data)
                objects.append(deserialized_obj)
            return objects

        # cache miss: load from DB + {key : list(序列化queryset: 才会执行SQL语句)}
        cls._load_objects_to_cache(key=key, objects=queryset)
        # 转换为 list 的原因是保持返回类型的统一，因为存在 redis 里的数据是 list 的形式
        return list(queryset)

    @classmethod
    def push_objects(cls, key, obj, queryset):  # 存
        conn = RedisClient.get_connection()
        if not conn.exists(key):
            # cache miss: 直接从数据库里 load
            # 就不走单个 push 的方式加到 cache 里了

            # 例: 缓存过期后，user新发了一条推文，如果 "走单个 push 的方式加到 cache 里"
            #     那user之前发的推文，就全部丢失了; 所以应该直接从数据库里 load
            cls._load_objects_to_cache(key=key, objects=queryset)
            return
        # cache hit [lpush: 把新的帖子加到最左边]
        serialized_data = DjangoModelSerializer.serialize(instance=obj)
        conn.lpush(key, serialized_data)