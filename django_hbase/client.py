import happybase
from django.conf import settings


class HBaseClient:
    conn = None

    @classmethod
    def get_connection(cls):
        if cls.conn:
            return cls.conn
        # 仅需要提供HOST, 不需要提供用户名和密码;
        # 所以 HBase 一般会设置权限, 仅内部访问
        cls.conn = happybase.Connection(host=settings.HBASE_HOST)
        return cls.conn