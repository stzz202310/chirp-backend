from testing.testcases import TestCase
from utils.redis_client import RedisClient


class UtilsTests(TestCase):

    def setUp(self):
        # super(UtilsTests, self).setUp()
        self.clear_cache()

    def test_redis_client(self):
        conn = RedisClient().get_connection()
        # Redis/数据库二进制存储, 网络传输(socket), 文件读取(以'rb'打开), Django请求体
        # b'2'.decode() ==> '2'
        # '2'.encode()  ==> b'2'
        conn.lpush('redis_key', 1)  # <class 'bytes'>
        conn.lpush('redis_key', 2)
        cached_list = conn.lrange('redis_key', 0, -1)   # 左闭右闭：从第一个到最后一个
        self.assertEqual(cached_list, [b'2', b'1'])

        RedisClient.clear()
        cached_list = conn.lrange('redis_key', 0, -1)
        self.assertEqual(cached_list, [])