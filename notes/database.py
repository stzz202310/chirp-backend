"""""""""
python manage.py shell

from tweets.models import Tweet
qs = Tweet.objects.all()
print(qs.query)

========================================================================================================

1. 不要用 JOIN
    例子: friendships.services | comments.api.views
    ❌select_related, ✅prefetch_related
    
    a. JOIN 本身并不快 [Web后端需要秒回, 不要用JOIN]
    b. JOIN 必须在同一实例内执行 [同一个 MySQL 进程里, 同一物理机器上]
        当你做了 sharding：
        shard_1：运行 MySQL 实例 #1（存 user 表）
        shard_2：运行 MySQL 实例 #2（存 friendship 表）
        它们是两个不同的实例 (不同进程、不同机器), MySQL 做不到跨实例 JOIN, JOIN 失效

2. 不要用 CASCADE 
    删除一个用户 -> 删除这个用户发的帖子 -> 删除帖子的赞和评论 -> 删除评论的赞 ...

3. DROP FOREIGN KEY CONSTRAINT {TODO [HARD]}

4. N + 1 Queries: 1个 API request 对应 常数级别的 DB queries [10次]
    例子: newsfeeds.services｜friendships.services | comments.api.views
    例子: utils.redis_helper| 
    ❌for 循环 {Query 多次查找}, ✅prefetch_related
    ❌for 循环 {Query 多次插入}, ✅bulk_create
    ❌for 循环 {redis 多次插入}, ✅conn.rpush(key, *serialized_list)
    ❌for 循环 {cache.get(key)},✅memcached.get_many([keys])
    
    web (client) <==> db|redis|memcached (server) 不同机器 需要数据传输和校验
    假设 通讯时间(roundtrip time) 10ms，SQL操作时间 1ms
    通讯十次 每次插入一条[错误] = (10 + 1) * 10 = 110 ms
    通讯一次 每次插入十条[正确] = 10 + 1 * 10 = 20 ms

5. Table.objects.filter(...).filter(...) 有多个筛选条件时，一定要检查是否有 联合索引 ⚠️
   Table.objects.filter(...).filter(...) 会整合为一条 SQL 语句
   
   queryset = Tweet.objects.filter(...)[:21]
   A. if len(queryset) == 21:     ✅
   B. if queryset.count() == 21:  ❌ 会产生一条query语句, SELECT Count(*) FROM `tweets_tweet` WHERE ...

========================================================================================================

排序 [不会对数据库产生影响，只会影响 QuerySet]
1. class Tweet(models.Model): class Meta: ordering = ('-created_at',)       不推荐，潜规则
2. tweets = Tweet.objects.filter(user_id=user_id).order_by('-created_at')   推荐，明显直观 [2会覆盖1]

=============================================================

(1) 更改 models
(2) makemigrations   ← 让迁移文件跟上你的代码
(3) test             ← 使用包含 {最新迁移文件} 的测试数据库
(4) 如果有问题 再次修改 ← 重复1-3
(5) migrate          ← 应用到正式数据库

========================================================================================================

劝和不劝分: 能不能仅用参数区分 like comment / like tweet
劝分不劝和: 一个 app 可以有多个 Models
    1. 方便拆分到不同的机器|不同类型的数据库中: 各个表单的读写频率不同
        User:           登陆,注册[频率低]
        UserProfile:    个人信息展示[频率高]
        PushPreference: 推送的时候[频率高]
    
    2. 数据库访问频率低: 使用MySQL单表即可
       数据库访问频率高: 水平拆分(sharding) 或 分布式存储(HBase|MongoDB), 相当于多个人一起工作 分摊访问压力
       单条数据访问频率极高: 复制 N 份，让流量打到不同的机器
       
    3. 把 User 与 UserProfile 拆开，可以让缓存也按“变化频率”分离，直接提高缓存命中率 cache hit
       拆分 User / UserProfile = 分缓存 = 减少缓存 miss、提升 hit 率、降低缓存 I/O 开销
       避免 "为了获取 username 却把整个 profile 拉出来" | "profile的更新 导致User缓存失效"


class User(models.Model):
class UserProfile(models.Model):
class PushPreference(models.Model):

    class Meta: 配置信息
        db_table = 'app_model'  default
        db_table = 'XXX'        自定义

========================================================================================================

like_set, has_liked, likes_count
方法 1: models.py
    @property
    def like_set(self 尽量不要带其他的参数):
    +
    class TweetSerializerForDetail(TweetSerializer):
        likes = LikeSerializer(source='like_set', many=True)

方法 2: api.serializers.py 
    A. 通过计算得到, 仅 Like Model 的信息不够, 所以不放在 models.py
    B. models 是最底层，尽量不要有其他依赖 [views, serializers, services 都会依赖 models]

    comments = serializers.SerializerMethodField()
    def get_comments(self, obj):
        self: serializer
        obj: tweet
        return CommentSerializer(obj.comment_set.all(), many=True).data
        # comments = CommentSerializer(...):  DRF 帮你自动调用了 .data           [不需要手动 .data]
        # return CommentSerializer(...).data: 你控制序列化过程，必须手动返回序列化结果 [需要手动 .data]
    当前类 及其 子类 [TweetSerializer, TweetSerializerForDetail]
    class Meta: fields = (⚠️'comments',)

方法 3: related_name(models.py) + source(api.serializers.py)
    Friendship 的多个 ForeignKey 都指向 User
    from_user = models.ForeignKey(User, related_name='following_friendship_set',)
    to_user = models.ForeignKey(User, related_name='follower_friendship_set',)

    class FollowerSerializer(serializers.ModelSerializer):      # 粉丝列表
        user = UserSerializerForFriendship(source='from_user')
    class FollowingSerializer(serializers.ModelSerializer):
        user = UserSerializerForFriendship(source='to_user')

    class TweetSerializerForDetail(TweetSerializer):
        comments = CommentSerializer(source='comment_set', many=True)   # queryset = tweet.comment_set
        likes = LikeSerializer(source='like_set', many=True)

    publisher = UserSerializer()              自动去找 tweet.publisher
    publisher = UserSerializer(source='user') 自动去找 tweet.user; 必须在 meta.fields 中也定义publisher
    
========================================================================================================

user [1 request] ==> web server [10 DB queries] ==> DB [100 I/O] ==> Disk 硬盘

1 request: ~ 10 DB queries
1 DB query ~ 10 Disk I/O 操作
web server: 轻量级的运算，所以可以用 python

RateLimit: 限制 request, 保护 DB
✅ 数据存储在 cache [临时需要的数据 + 能支持更大的 QPS]
   cache 作为盾，挡住大部分的请求，保护 DB
❌ 数据存储在 webserver.local variable
   user [1st request] ==> load balancer ==> web server1
   user [2nd request] ==> load balancer ==> web server2

=============================================================

action:     login
rate limit: 5/min
feature: 未登录 ip, 已登陆 user_id, 手机验证 手机号 


1. 令牌法                  TODO [Homework]: 自己实现
key: "ip + action"
用户 A [192.168.0.1] 1min内 第1次登陆 (⚠️memcached: 比 redis 更快)
cache.set{key:val} = {"192.168.0.1_login":4, timeout=1min}
用户 A [192.168.0.1] 1min内 第2次登陆
cache.set{key, cache.get(key) - 1 = 3}
用户 A [192.168.0.1] 1min内 第6次登陆 block

缺点: "1min窗口"的定义并不是特别精确，大概限制
例子: [0 57 58 59 60] [61 62 63 64 65]    窗口[57 65] 一共登陆了9次


2. django-ratelimit 优化      TODO [Homework]: 自己实现
key: "ip + action + created_at"
用户 A [192.168.0.1] 登陆 key: {"192.168.0.1_login_20251212:10:10:59"}
前01秒key {"192.168.0.1_login_20251212:10:10:58"}
前02秒key {"192.168.0.1_login_20251212:10:10:57"}
...
前59秒key {"192.168.0.1_login_20251212:10:10:00"}
前60秒key {"192.168.0.1_login_20251212:10:09:59"}
if sum(cache.get(key) + cache.get(前01秒key) ... + cache.get(前60秒key)) > 5: block

5/min: created_at 精确到 秒
5/hour:created_at 精确到 分钟
5/day: created_at 精确到 小时

缺点: 60次 cache.get 请求
优化: memcached get_many([keys])  节省 [webserver <==> cache] 机器之间的通讯时间

========================================================================================================
┌─────────────┐
│ Django App  │
└──────┬──────┘
       ├── MySQL       → 127.0.0.1:3306
       ├── Redis       → 127.0.0.1:6379
       ├── Memcached   → 127.0.0.1:11211
       └── HBase       → 127.0.0.1:9090 (Thrift)

0.0.0.0:   监听所有网卡
127.0.0.1: 只监听本机

Django 测试环境中的数据清理规则
1. Django 会自动处理的部分:   MySQL (仅限 DATABASES 中配置的数据库)
2. Django 不会自动处理的部分: ⚠️ memcached, redis, HBase, Celery broker
   因为它们 不受 Django ORM / TestRunner 控制, 需要手动清理

class TestCase(DjangoTestCase):

    def setUp(self):    # setUp 会在每个 test_xxx 运行前 被执行
        self.clear_cache()
        hbase_model_class.create_table()

    def tearDown(self): # tearDown 会在每个 test_xxx 运行后 被执行
        hbase_model_class.drop_table()

"""