from django.conf import settings

from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer


class RedisHelper:

    @classmethod
    def _load_objects_to_cache(cls, key, objects):
        conn = RedisClient.get_connection()

        serialized_list = []
        # 最多只 cache REDIS_LIST_LENGTH_LIMIT 这么多个 objects
        # 超过这个限制的 objects, 就去数据库里读取。一般这个限制会笔记大，比如 200
        # 因为翻页翻到 第201条数据 的用户|访问量会比较少，从数据库读取也不是大问题
        # 特别是 EndlessPagination 瀑布流数据，用户需要向下滑动很久 才能到 第201条数据
        for obj in objects[:settings.REDIS_LIST_LENGTH_LIMIT]:
            # serialized_data = DjangoModelSerializer(数据库的原始数据),
            # serialized_data: 没有经过 ModelSerializer
            # b'[{ "model": "newsfeeds.newsfeed", "pk": 15,
            #   "fields": {"user": 3, "tweet": 14, "created_at": "2025-12-12T19:06:45.300033Z"}}]'
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
        # ⚠️ 返回的是 数据库中的数据，不是当前cache中的数据
        # len(queryset) >= len(objects) AND len(objects) <= settings.REDIS_LIST_LENGTH_LIMIT
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
        # ltrim: 想要留下的区间 [start, end]
        conn.ltrim(name=key, start=0, end=settings.REDIS_LIST_LENGTH_LIMIT-1)

    @classmethod
    def get_count_key(cls, obj, attr):
        # Tweet.likes_count:<tweet.id>
        return '{}.{}:{}'.format(obj.__class__.__name__, attr, obj.id)

    @classmethod
    def incr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj=obj, attr=attr)
        # if not conn.exists(key):
        #     conn.set(name=key, value=getattr(obj, attr))
        #     conn.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)
        #     return getattr(obj, attr)
        # return conn.incr(name=key)
        if conn.exists(key):
            # cache hit
            return conn.incr(key)   # 返回 +1 后的值

        # cache miss, read from DB
        # 必须保证调用 def incr_count() 之前，obj.attr 已经 +1 过了
        obj.refresh_from_db()
        count = getattr(obj, attr)  # count = obj.__dict__.get(attr)
        conn.set(name=key, value=count)
        conn.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)
        return count

    @classmethod
    def decr_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj=obj, attr=attr)
        if conn.exists(key):
            # cache hit
            return conn.decr(name=key)

        obj.refresh_from_db()
        count = getattr(obj, attr)
        conn.set(name=key, value=count)
        conn.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)
        return getattr(obj, attr)

    @classmethod
    def get_count(cls, obj, attr):
        conn = RedisClient.get_connection()
        key = cls.get_count_key(obj=obj, attr=attr)
        count = conn.get(key)
        if count is not None:
            return int(count)

        obj.refresh_from_db()
        count = getattr(obj, attr)
        conn.set(name=key, value=count)
        conn.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)
        return count