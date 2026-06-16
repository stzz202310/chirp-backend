import logging

from django.conf import settings
from redis.exceptions import RedisError

from django_hbase.models import HBaseModel
from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer, HBaseModelSerializer
from utils.time_constants import ONE_MINUTE

logger = logging.getLogger(__name__)


class RedisHelper:
    # 存储结构: Redis List，按 created_at 倒序 (最新在左 lpush，最旧在右 rpush)
    # 最大缓存: REDIS_LIST_LENGTH_LIMIT (如 200)
    # 超出限制: 直接读数据库 (瀑布流场景下翻到第200条的用户极少)

    @classmethod
    def _load_objects_to_cache(cls, key, objects, serializer): # 从数据库读取并放入缓存
        # 全量重建: 先 DEL 再 RPUSH, 整体替换
        conn = RedisClient.get_connection()
        pipeline = conn.pipeline()
        pipeline.delete(key)
        serialized_list = [serializer.serialize(instance=obj) for obj in objects]
        if serialized_list:
            pipeline.rpush(key, *serialized_list)
        pipeline.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)
        pipeline.execute()  # del+rpush+expire 一次性原子执行

    @classmethod
    def load_objects(cls, key, lazy_load_objects, serializer=DjangoModelSerializer):    # 读取 objects
        conn = RedisClient.get_connection()
        try:
            # 1. cache hit: 直接从cache取全部 → [逐条]反序列化 → 返回 list
            if conn.exists(key):
                return cls._load_objects_cache_hit(key=key, serializer=serializer)

            # 2. cache miss: load from DB → 写入 cache → 返回 list (与 cache hit 的返回类型保持一致)
            # ⚠️ 关键不变式: cache-miss 分支永远 "整体重建" 而非 "追加", 且重建受锁保护
            with conn.lock(f'{key}:lock', timeout=ONE_MINUTE):  # cache miss: 加锁串行重建
                if conn.exists(key):    # double-check: 等锁期间别人已建好
                    return cls._load_objects_cache_hit(key=key, serializer=serializer)
                objects = lazy_load_objects(limit=settings.REDIS_LIST_LENGTH_LIMIT)
                cls._load_objects_to_cache(key=key, objects=objects, serializer=serializer)
                return list(objects)
        except RedisError as e:
            # Redis 故障: 缓存是 best-effort, 降级直读 DB, 保证功能可用 (本次不缓存)
            logger.warning('load_objects fallback to DB, key=%s, err=%s', key, e)
            return list(lazy_load_objects(limit=settings.REDIS_LIST_LENGTH_LIMIT))

    @classmethod
    def _load_objects_cache_hit(cls, key, serializer):
        conn = RedisClient.get_connection()
        serialized_list = conn.lrange(name=key, start=0, end=-1)
        objects = []
        for serialized_data in serialized_list:
            deserialized_obj = serializer.deserialize(serialized_data=serialized_data)
            objects.append(deserialized_obj)
        return objects

    @classmethod
    def push_objects(cls, key, obj, lazy_load_objects):  # 保存 objects
        # lazy_load_objects: 现已不在 push 里重建, 故未使用; 保留入参与 load_objects 对称, 调用方无需改动
        if isinstance(obj, HBaseModel):
            serializer = HBaseModelSerializer
        else:
            serializer = DjangoModelSerializer

        conn = RedisClient.get_connection()
        try:
            # 只在缓存已存在(热)时增量 lpush; 缓存不存在(冷)时直接返回, 不在 push 里重建。
            # 冷缓存交给读路径 load_objects 惰性重建 (来龙去脉见 docs/database/design/consistency.txt 第 5 节)
            if not conn.exists(key):
                return
            # cache hit: lpush 新的帖子加到最左边 -> ltrim 保持最大长度 [start, end]
            serialized_data = serializer.serialize(instance=obj)
            conn.lpush(key, serialized_data)
            conn.ltrim(name=key, start=0, end=settings.REDIS_LIST_LENGTH_LIMIT - 1)
        except RedisError as e:
            # Redis 故障: push 是 best-effort, 跳过即可; 下次读 cache miss 会从 DB 重建出完整快照
            logger.warning('push_objects skipped, key=%s, err=%s', key, e)

    @classmethod
    def get_count_key(cls, obj, attr):
        # Tweet.likes_count:{tweet.id}
        return '{}.{}:{}'.format(obj.__class__.__name__, attr, obj.id)

    @classmethod
    def incr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj=obj, attr=attr)
        try:
            if conn.exists(key):
                return conn.incr(name=key, amount=1)   # 返回 +1 后的值
            # 注意: 调用 incr_count() 之前，必须确保 obj.attr 已经在数据库中完成 +1
            obj.refresh_from_db()
            count = getattr(obj, attr)
            # set + 过期一次性写入 (原子, 避免崩在两条命令之间导致 key 永不过期)
            conn.set(name=key, value=count, ex=settings.REDIS_KEY_EXPIRE_TIME)
            return count
        except RedisError as e:
            # Redis 故障: 退回 DB 真值 (调用前已确保 DB 完成 +1)
            logger.warning('incr_count fallback to DB, key=%s, err=%s', key, e)
            obj.refresh_from_db()
            return getattr(obj, attr)

    @classmethod
    def decr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj=obj, attr=attr)
        try:
            if conn.exists(key):
                return conn.decr(name=key)
            obj.refresh_from_db()
            count = getattr(obj, attr)
            conn.set(name=key, value=count, ex=settings.REDIS_KEY_EXPIRE_TIME)
            return count
        except RedisError as e:
            logger.warning('decr_count fallback to DB, key=%s, err=%s', key, e)
            obj.refresh_from_db()
            return getattr(obj, attr)

    @classmethod
    def get_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj=obj, attr=attr)
        try:
            count = conn.get(name=key)
            if count is not None:
                return int(count)
            obj.refresh_from_db()
            count = getattr(obj, attr)
            conn.set(name=key, value=count, ex=settings.REDIS_KEY_EXPIRE_TIME)
            return count
        except RedisError as e:
            logger.warning('get_count fallback to DB, key=%s, err=%s', key, e)
            obj.refresh_from_db()
            return getattr(obj, attr)