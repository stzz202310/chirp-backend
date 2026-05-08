from testing.testcases import TestCase
from utils.redis_client import RedisClient


class UtilsTests(TestCase):

    def setUp(self):
        # super(UtilsTests, self).setUp()
        self.clear_cache()

    def test_redis_client(self):
        conn = RedisClient().get_connection()
        # Redis 以二进制存储，读取结果为 bytes
        conn.lpush('redis_key', 1)                      # [1]
        conn.lpush('redis_key', 2)                      # [2, 1] ← 2 插入到头部[最左边]
        cached_list = conn.lrange('redis_key', 0, -1)   # 从左到右取，2 在头部所以先取出来
        self.assertEqual(cached_list, [b'2', b'1'])

        RedisClient.clear()
        cached_list = conn.lrange('redis_key', 0, -1)
        self.assertEqual(cached_list, [])