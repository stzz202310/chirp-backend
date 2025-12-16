import redis
from django.conf import settings


class RedisClient:
    conn = None # 整个类 全局共享 coon

    # request ==> web server [1 process] ==> response
    # 1 request 可能等于 10 x redis get 加 10 x redis set
    # 1 request 只建立一个 connection，不要建立多个 connections
    @classmethod
    def get_connection(cls):
        # 使用 singleton 模式，全局只创建一个 connection
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
        conn.flushdb()  # 类似于 caches['testing'].clear()