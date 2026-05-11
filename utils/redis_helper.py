from django.conf import settings

from django_hbase.models import HBaseModel
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer, HBaseModelSerializer


class RedisHelper:
    # 存储结构: Redis List，按 created_at 倒序 (最新在左 lpush，最旧在右 rpush)
    # 最大缓存: REDIS_LIST_LENGTH_LIMIT (如 200)
    # 超出限制: 直接读数据库 (瀑布流场景下翻到第200条的用户极少)

    @classmethod
    def _load_objects_to_cache(cls, key, objects, serializer): # 从数据库读取并放入缓存
        conn = RedisClient.get_connection()
        serialized_list = []
        for obj in objects:
            serialized_data = serializer.serialize(instance=obj)
            serialized_list.append(serialized_data)

        if serialized_list:
            conn.rpush(key, *serialized_list)
            conn.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)

    @classmethod
    def load_objects(cls, key, lazy_load_objects, serializer=DjangoModelSerializer):    # 读取 objects
        conn = RedisClient.get_connection()

        # 1. cache hit: 直接从cache取全部 → [逐条]反序列化 → 返回 list
        if conn.exists(key):
            serialized_list = conn.lrange(name=key, start=0, end=-1)
            objects = []
            for serialized_data in serialized_list:
                deserialized_obj = serializer.deserialize(serialized_data=serialized_data)
                objects.append(deserialized_obj)
            return objects

        # 2. cache miss: load from DB → 写入 cache → 返回 list (与 cache hit 的返回类型保持一致)
        objects = lazy_load_objects(limit=settings.REDIS_LIST_LENGTH_LIMIT)
        cls._load_objects_to_cache(key=key, objects=objects, serializer=serializer)
        return list(objects)

    @classmethod
    def push_objects(cls, key, obj, lazy_load_objects):  # 保存 objects
        if isinstance(obj, HBaseModel):
            serializer = HBaseModelSerializer
        else:
            serializer = DjangoModelSerializer

        conn = RedisClient.get_connection()
        # 1. cache hit: lpush 新的帖子加到最左边 → ltrim 保持最大长度 [start, end]
        if conn.exists(key):
            serialized_data = serializer.serialize(instance=obj)
            conn.lpush(key, serialized_data)
            conn.ltrim(name=key, start=0, end=settings.REDIS_LIST_LENGTH_LIMIT - 1)
            return

        # 2. cache miss: 直接从数据库里全量加载写入缓存, 不走单个 push 的方式加到 cache 里
        # 例: 缓存过期后，user新发了一条推文，如果 "走单个 push 的方式加到 cache 里"
        #     那user之前发的推文，就全部丢失了; 所以应该直接从数据库里全量加载写入缓存

        # queryset = queryset[:settings.REDIS_LIST_LENGTH_LIMIT]
        # 切片操作返回新的 QuerySet (惰性求值，尚未执行 SQL)
        objects = lazy_load_objects(limit=settings.REDIS_LIST_LENGTH_LIMIT)
        cls._load_objects_to_cache(key=key, objects=objects, serializer=serializer)

    @classmethod
    def get_count_key(cls, obj, attr):
        # Tweet.likes_count:{tweet.id}
        return '{}.{}:{}'.format(obj.__class__.__name__, attr, obj.id)

    @classmethod
    def incr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj=obj, attr=attr)
        if conn.exists(key):
            return conn.incr(name=key, amount=1)   # 返回 +1 后的值

        # 注意: 调用 incr_count() 之前，必须确保 obj.attr 已经在数据库中完成 +1
        obj.refresh_from_db()
        count = getattr(obj, attr)
        conn.set(name=key, value=count)
        conn.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)
        return count

    @classmethod
    def decr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj=obj, attr=attr)
        if conn.exists(key):
            return conn.decr(name=key)

        obj.refresh_from_db()
        count = getattr(obj, attr)
        conn.set(name=key, value=count)
        conn.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)
        return count

    @classmethod
    def get_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj=obj, attr=attr)
        count = conn.get(name=key)
        if count is not None:
            return int(count)

        obj.refresh_from_db()
        count = getattr(obj, attr)
        conn.set(name=key, value=count)
        conn.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)
        return count