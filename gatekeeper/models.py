from utils.redis_client import RedisClient


class GateKeeper(object):

    @classmethod
    def get(cls, gk_name):
        conn = RedisClient.get_connection()
        name = f'gatekeeper:{gk_name}'
        if not conn.exists(name):
            return {'percent': 0, 'description': ''}

        redis_hash = conn.hgetall(name=name)
        return {
            'percent': int(redis_hash.get(b'percent', 0)),
            'description': str(redis_hash.get(b'description', ''))
        }

    @classmethod
    def set_kv(cls, gk_name, key, value):
        conn = RedisClient.get_connection()
        name = f'gatekeeper:{gk_name}'
        conn.hset(name=name, key=key, value=value)

    @classmethod
    def is_switch_on(cls, gk_name):
        percent = cls.get(gk_name=gk_name)['percent']
        # 'gatekeeper:switch_friendship_to_hbase': {'percent': XX, 'description': 'XXX'}
        # percent == 100: switch on  [Hbase]
        # percent <  100: switch off [MySQL]
        return percent == 100

    @classmethod
    def turn_on(cls, gk_name):
        cls.set_kv(gk_name=gk_name, key='percent', value=100)

    @classmethod
    def in_gk(cls, gk_name, user_id):
        percent = cls.get(gk_name=gk_name)['percent']
        return user_id % 100 < percent