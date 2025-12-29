from django.conf import settings

from utils.redis_client import RedisClient
from utils.redis_serializers import DjangoModelSerializer


class RedisHelper:

    @classmethod
    def _load_objects_to_cache(cls, key, objects):
        conn = RedisClient.get_connection()
        serialized_list = []
        for obj in objects:
            # print(obj.__dict__) 数据库的原始数据
            # {'_state': <django.db.models.base.ModelState object at 0xffffb1980160>,
            #  'id': 1,
            #  'user_id': 1,
            #  'content': 'hello zhuzhu',
            #  'created_at': datetime.datetime(2025, 12, 29, 5, 7, 48, 190038, tzinfo=<UTC>),
            #  'likes_count': 0,
            #  'comments_count': 0}

            serialized_data = DjangoModelSerializer.serialize(instance=obj)
            # print(serialized_data)    字符串 str
            # [{"model": "tweets.tweet",
            #   "pk": 1,
            #   "fields": {
            #       "user": 1,
            #       "content": "hello zhuzhu",
            #       "created_at": "2025-12-29T05:11:16.530588Z",
            #       "likes_count": 0,
            #       "comments_count": 0}}]
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
        # 1. len(缓存中的数据) <= len(数据库中的数据) AND
        # 2. len(缓存中的数据) <= settings.REDIS_LIST_LENGTH_LIMIT
        # 通过切片方式, 只取 queryset 的前 REDIS_LIST_LENGTH_LIMIT 条数据,
        # 防止一次性从数据库读取过多数据，降低数据库压力和内存占用

        # 最多只 cache REDIS_LIST_LENGTH_LIMIT 这么多个 objects
        # 超过这个限制的 objects, 就去数据库里读取。一般这个限制会笔记大，比如 200
        # 因为翻页翻到 第201条数据 的用户|访问量会比较少，从数据库读取也不是大问题
        # 特别是 EndlessPagination 瀑布流数据，用户需要向下滑动很久 才能到 第201条数据
        queryset = queryset[:settings.REDIS_LIST_LENGTH_LIMIT]
        conn = RedisClient.get_connection()

        # cache hit: 直接拿出来，然后返回
        if conn.exists(key):
            # [左闭右闭，从左向右全部取出来]
            serialized_list = conn.lrange(name=key, start=0, end=-1)
            objects = []
            for serialized_data in serialized_list:
                # 逐条反序列化数据 (而不是一次性处理全部)
                deserialized_obj = DjangoModelSerializer.deserialize(serialized_data=serialized_data)
                objects.append(deserialized_obj)
            return objects

        # cache miss: load from DB + {key : list(序列化queryset: 才会执行SQL语句)}
        cls._load_objects_to_cache(key=key, objects=queryset)
        # 转换为 list 的原因是保持返回类型的统一，因为存在 redis 里的数据是 list 的形式
        return list(queryset)

    @classmethod
    def push_objects(cls, key, obj, queryset):  # 存
        queryset = queryset[:settings.REDIS_LIST_LENGTH_LIMIT]
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
            return conn.incr(name=key, amount=1)   # 返回 +1 后的值

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
        count = conn.get(name=key)
        if count is not None:
            return int(count)

        obj.refresh_from_db()
        count = getattr(obj, attr)
        conn.set(name=key, value=count)
        conn.expire(name=key, time=settings.REDIS_KEY_EXPIRE_TIME)
        return count

"""
  | 数据结构| 命令示例                | 逻辑结构               |
  | ------ | --------------------- | --------------------  |
1 | String | SET key value         | key → value           |
2 | Hash   | HSET key field value  | key → (field → value) |
3 | List   | LPUSH key value       | key → [v1, v2, ...]   |
4 | Set    | SADD key value        | key → {v1, v2}        |
5 | ZSet   | ZADD key score member | key → {member: score} |

1. String
conn.set(name=key, value=value)
conn.get(name=key)
conn.exists(name=key)
conn.delete(name=key)
conn.expire(name=key, time=秒)
conn.incr(name=key, amount=1)   # 只适用于整数值
conn.decr(name=key, amount=1)

2. Hash
conn.hset(name=key, key=field, value=value)
conn.hset(name=key, mapping={'field1': 'v1', 'field2': 'v2'})
conn.hgetall(name=key)
conn.hget(name=key, key=field)
conn.exists(name=key)
conn.hexists(name=key, key=field)
conn.hdel(name=key, key=field)

3. List
conn.lpush(name=key, value=value)   | conn.rpush
conn.lpop(name=key)                 | conn.rpop
conn.lrange(name=key, start=0, stop=-1) # 获取列表切片, stop=-1 表示取到最后一个元素
conn.ltrim(name=key, start=0, stop=-1)  # 保留指定区间元素，其他删除
conn.llen(name=key)                     # 列表长度

4. Set
conn.sadd(name=key, value)           # 添加元素
conn.smembers(name=key)              # 获取所有元素
conn.srem(name=key, value)           # 删除元素
conn.sismember(name=key, value)      # 判断是否存在
conn.scard(name=key)                 # 集合大小

2. Hash key → {field1: value1, field2: value2, ...}
5. ZSet key → {member1: score1, member2: score2, ...}  # 有序集合, 内部自动按 score 从小到大默认排序

"""