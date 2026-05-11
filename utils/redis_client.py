import redis
from django.conf import settings


class RedisClient:
    conn = None
    # 类属性 conn: 所有实例共享同一个连接(全局共享), 避免重复创建 Redis 连接
    # 一个 request 的生命周期 可能会执行 10 次 Redis GET + 10 次 Redis SET
    # 因此, 1 个 request 应复用 1 个 Redis connection

    @classmethod
    def get_connection(cls):
        if cls.conn:    # if RedisClient.conn:
            return cls.conn
        cls.conn = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
        )
        return cls.conn

    @classmethod
    def clear(cls):
        # clear all keys in redis, for testing purpose ONLY
        if not settings.TESTING:
            raise Exception("You can not flush redis in production environment")
        conn = cls.get_connection()
        conn.flushdb()  # ⚠️ 测试环境: Redis/Gatekeeper/Celery 的数据都会被清空