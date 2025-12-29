from utils.redis_client import RedisClient


class Gatekeeper(object):

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
        # percent == 100: switch on [switch_friendship_to_hbase]
        # percent <  100: switch off[switch_friendship_to_hbase]
        return percent == 100

    @classmethod
    def in_gk(cls, gk_name, user_id):
        # 根据 gk_name 获取灰度百分比 (0 ~ 100)
        percent = cls.get(gk_name=gk_name)['percent']
        # 灰度规则说明：
        # 1. percent == 100：所有用户命中灰度  (全部走新逻辑)
        # 2. percent == 0  ：所有用户不命中灰度(全部走旧逻辑)
        #
        # 3. 使用 user_id % 100 作为稳定分桶策略：
        #    - 同一个 user_id 的结果始终固定，不会来回切换
        #    - 灰度比例从小到大扩展时，已命中的用户仍然命中
        #
        # 示例：
        #   user_id = 5
        #   percent = 0   → False
        #   percent = 10  → 5 % 100 < 10  → True
        #   percent = 20  → 5 % 100 < 20  → True
        #   percent = 100 → True

        # 判断当前用户是否命中灰度
        return user_id % 100 < percent

"""
一 数据库切换场景分析 [MySQL -> HBase]
1. 未上线系统（无历史数据）
   - 可以直接删除 Django ORM 的 models.py
   - 使用 hbase_models.py 作为唯一数据模型
   - 不存在数据迁移问题，切换成本低

2. 已上线系统（存在线上数据）
   - MySQL 中已经有真实用户数据
   - 不能直接删除 ORM 或切换数据库, 否则会导致历史数据丢失
   - 必须采用「新老数据库并存 + 灰度切换」方案

3. 数据库迁移 / 表结构调整原则
   - 适用于以下场景: MySQL -> HBase, 数据库拆分, 表结构重构, 大表|大字段拆分
   - 核心原则：新表|新库|新逻辑 和 旧表|旧库|旧逻辑 必须在一段时间内同时存在


二 灰度发布（Gray Release）
- 常见灰度流程：percent = 0% -> 20% -> 100%
  0%   : 所有用户走旧逻辑（仅部署代码，不生效）
  20%  : 小部分用户走新逻辑（灰度测试）
  100% : 全量用户切换到新逻辑(正式上线)

- 新功能上线可能存在: Bug, 性能问题, 用户体验不佳
  1. 传统回滚方式: revert commit + deploy [回滚成本高，响应慢]
  2. GateKeeper: 支持已部署代码的 即时生效|即时撤回, 无需重新部署
     快速止损: 100% -> 0% 可立即生效

- GateKeeper [功能开关|灰度开关]
  Redis: 访问频率非常高(每次请求几乎都会判断)
"""