class HBaseField:
    field_type = None

    def __init__(self, reverse=False, column_family=None):
        self.reverse = reverse
        self.column_family = column_family
        # TODO [Homework]
        # 增加 is_required 属性, 默认为 true
        # 增加 default 属性，默认为 None
        # 并在 hbase model 中做相应的处理, 抛出相应的异常信息

        """
        HBase / 分布式数据库中的数据热点问题
        
        数据热点 (Hotspot)
        1. 数据按 RowKey 的字典序 分布在不同 Region / 机器上
        2. 如果 RK 单调递增(时间, ID), 新数据会集中写入到同一台或少数几台机器
        导致: 写入热点; 读取热点; 集群负载不均
        
        friendships 用户关注
        1. user_id 越大 → 注册时间越晚 [新用户的 user_id 较大]
        2. 新用户: 登录频繁; 点关注 | 被关注频繁
           老用户: 行为稳定; 新关注频率低
        
        总结: 新数据访问频率高，旧数据访问频率低
        
        ============================================================
        
        ❌ RowKey 设计1 (容易产生热点)
        rk = user_id + created_at
        1. user_id, created_at 都是 单调递增
        2. 数据按顺序写入: 新数据集中在 RK 尾部
        
        机器1         机器2      机器3
        旧数据(低频)   中数据     新数据(高频 => 热点问题)
        
        分布式数据库的意义是 均摊访问量, 而不是按新旧程度分布
        
        
        ✅ RowKey 设计2 (反转 Reversing: 打散顺序性, 让新数据均匀分布到不同机器)
        rk = reverse(user_id) + created_at
        user_id = 2132 =   0000 0000 0000 2132
        reverse(user_id) = 2312 0000 0000 0000
        
        Padding(补零): 
        10  → reverse → 01 → 1
        100 → reverse → 001 → 1
        
        查询需求        
        ✅ user_id = XX, ❌ user_id 范围查询
        ✅ timestamp 范围查询
        
        反转: 有序 → 无序; 范围扫描失效
        ✅ user_id   可以反转
        ❌ timestamp 不能反转
        """


class IntegerField(HBaseField):
    field_type = 'int'

    # def __init__(self, *args, **kwargs):
    #     # 自动调用 父类的 构造函数
    #     super(IntegerField, self).__init__(*args, **kwargs)


class TimestampField(HBaseField):
    field_type = 'timestamp'

    # def __init__(self, *args, auto_now_add=False, **kwargs):
    #     super(TimestampField, self).__init__(*args, **kwargs)