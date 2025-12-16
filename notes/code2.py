"""""""""
主机与虚拟机关系 [两台不同的机器]
- Host(宿主机): 你自己的电脑（macOS / Windows / Linux）
- Guest(来宾机): 在宿主机中运行的虚拟机
  - 使用 VirtualBox 提供虚拟化
  - 使用 Vagrant 进行虚拟机管理和环境自动配置
> 一个 GitHub repo 对应一个 Vagrant 虚拟机环境，便于项目隔离与可复现。

config.vm.network "forwarded_port", guest: 8000, host: 80
Guest VM 内部的 8000 端口 → 被映射到 Host 宿主机的 80 端口

config.vm.network "private_network", ip: "192.168.33.10"
宿主机可以直接访问虚拟机 IP 为 192.168.33.10，端口不变

ALLOWED_HOSTS = ["127.0.0.1", "localhost", "192.168.33.10"] # 允许宿主机访问虚拟机指定 IP
作用: 限制哪些域名/IP 可以访问 Django 应用，防止未经授权的请求。


python manage.py runserver 0.0.0.0:8000
1. 监听 0.0.0.0:8000 [本机所有 IPv4 地址的通配符, 绑定所有可用网络接口(不代表某一个 IP，本机有几个网卡就绑定几个)]
2. 含义：监听虚拟机所有网卡的 IP → 可被外部(同局域网)访问
3. 常用于在宿主机访问虚拟机中的 Django 服务

✅ 结论：宿主机能访问：
| 访问方式                     | 是否成功 | 原因                                |
| --------------------------- | ------ | ----------------------------------- |
| `http://localhost:80`       | ✅     | host:80 → forwarded to guest:8000  |
| `http://127.0.0.1:80`       | ✅     | 同上                                |
| `http://192.168.33.10:8000` | ✅     | 直连虚拟机私网 IP + 真实 8000 端口     |

❌ 宿主机不能访问：
| 访问方式                   | 是否成功 | 原因                             |
| ------------------------- | ------ | -------------------------------  |
| `http://localhost:8000`   | ❌     | 宿主机上并没有进程监听 8000         |
| `http://127.0.0.1:8000`   | ❌     | 同上                             |
| `http://192.168.33.10:80` | ❌     | 80 并没有映射回去，也没有在 VM 上监听 |


python manage.py runserver [127.0.0.1:8000]
[虚拟机]Django 的 runserver 会启动一个轻量级的 开发用 Web 服务器，默认监听 8000 端口
1. 监听 127.0.0.1:8000 [本机回环地址]
2. 只允许虚拟机内部访问   [同一台机器上启动的两个进程之间互相访问]
3. 宿主机或外部设备无法访问（因为只绑定到本地回环地址）

| 访问者                                       | 是否能访问  | 原因                         |
| ------------------------------------------- | --------- | ---------------------------- |
| 虚拟机内部自己访问 `http://127.0.0.1:8000`     | ✅ 可以   | 本机访问本机                   |
| 宿主机访问 `localhost:8000`|`127.0.0.1:8000` | ❌ 不行    | 宿主机和虚拟机是两个不同的“本机”  |
| 宿主机访问 `192.168.33.10:8000`              | ❌ 不行    | Django 没监听虚拟机的对外网络接口 |

=============================================================================================

宿主机浏览器 → (localhost:80) → Vagrant 转发 → VM NAT 网卡 (10.0.2.15:8000) 
→ Django 监听 0.0.0.0:8000 → Django 处理请求 → 返回网页 → 宿主机浏览器显示

1. 宿主机 浏览器打开 http://localhost:80 [实际访问的是 宿主机的 127.0.0.1:80]

2. Vagrant 的端口转发规则生效 config.vm.network "forwarded_port", guest: 8000, host: 80
    宿主机 host:80 ==> Vagrant 就会将流量转发到 ==> 虚拟机 guest:8000
    宿主机 → Vagrant NAT → 虚拟机的NAT网卡IP(10.0.2.15:8000), ❌不会转发到其它网卡(127.0.0.1 / host-only)

3. python manage.py runserver 0.0.0.0:8000  在虚拟机所有网络接口上监听端口 8000
   python manage.py runserver 10.0.2.15:8000
    虚拟机里可能有这些接口: [lo]127.0.0.1, [host-only]192.168.33.10, [NAT]10.0.2.15, ...
    所以 Django 实际监听: 127.0.0.1:8000, 192.168.33.10:8000, 10.0.2.15:8000, 其他所有接口的 8000

4. ALLOWED_HOSTS = ["127.0.0.1", "localhost", "192.168.33.10"]
    宿主机请求: GET /  Host: localhost
    Vagrant 转发后，进入 VM 的 Django 请求头仍然是: Host: localhost
    因为你允许了 "localhost"，所以 Django 不会报错
    如果你没写 "localhost"，访问就会报 Invalid HTTP_HOST header

================================================================================================================

排序 [不会对数据库产生影响，只会影响 QuerySet]
1. class Tweet(models.Model): class Meta: ordering = ('-created_at',)       不推荐，潜规则
2. tweets = Tweet.objects.filter(user_id=user_id).order_by('-created_at')   推荐，明显直观 [2会覆盖1]

================================================================================================================

User    | Comment: name of model
user    | comment: instance of User
user_id | comment_id: the primary key of User (int)
users   | comments: list of users | queryset of User 

from_user       模型字段名|外键字段      接收 User 对象
from_user_id    数据库列               接收用户 ID（整数）

⚠️ 对象 → 用 from_user
⚠️ ID  → 用 from_user_id, 尽量用 id, 减少 query 的次数

⚠️ 模型索引/约束（index_together, UniqueConstraint）必须写 from_user（模型字段名）

1 Serializer 决定 validated_data 是 "对象" 还是 "ID"(需要在 serializer 中定义 XXX_id)
    class CommentSerializerForCreate(serializers.ModelSerializer):
        tweet_id = serializers.IntegerField()
        user_id = serializers.IntegerField()
        class Meta:
            model = Comment
            fields = ('tweet_id', 'user_id', 'content',)
    
    class CommentSerializer(serializers.ModelSerializer):
        user = UserSerializer()
        class Meta:
            model = Comment
            fields = ('id', 'tweet_id', 'user', 'content', 'created_at',)
            # fields =
            # 1 'tweet_id' ｜ 'tweet': 都只展示 tweet id
            # 2 'user' {user = UserSerializer()}: 展示 user 的详细信息

2 查询中可以灵活使用 from_user 或 from_user_id
    Friendship.objects.filter(from_user=user_obj)      # 传对象
    Friendship.objects.filter(from_user_id=user_id)    # 传 ID

================================================================================================================

(1) 更改 models
(2) makemigrations   ← 让迁移文件跟上你的代码
(3) test             ← 使用包含 {最新迁移文件} 的测试数据库
(4) 如果有问题 再次修改 ← 重复1-3
(5) migrate          ← 应用到正式数据库

================================================================================================================

TCP/IP 上的应用层协议: HTTP(短连接), Socket(长连接)                  payload 等价于 data 数据
WebSocket 用 HTTP 建立连接，但通信本身不再依赖 HTTP

HTTP:   request → response, 客户端主动发起         单向: 客户端向服务端发起请求  
Socket: 建立一次连接后保持, server 可主动发送数据     双向: 客户端/服务端都可发消息 

Push Notification: 即时推送, 不存储 [不需要在数据库里存 model]  手机端消息提醒
Notification: 存储型通知 [需要数据库 model 存储]               Twitter 或微博的站内通知, 可以在历史消息中查看
App 第一次安装并启动时: App向APNS注册设备token, 系统会建立一个{长连接 socket}到APNS的服务器，用于接收推送消息

A 点赞 B
A ==> HTTP [客户端主动发起请求 短连接] ==> Twitter Web Server [更新 Notification Model & 生成通知]
Twitter Web Server ==> HTTP ==> APNS 推送服务器 ==> socket ==> B 手机端
Twitter Web Server ==> HTTP ==> Twitter Push Server ==> WebSocket ==> B Web端

================================================================================================================

class CommentViewSet(viewsets.GenericViewSet):
    filterset_fields = ('tweet_id',)
    
    def list(self, request, *args, **kwargs):
        queryset = Comment.objects.all()
        queryset = self.get_queryset()
        
        # comments = queryset.filter(tweet_id=request.query_params.get('tweet_id'))
        comments = self.filter_queryset(queryset=queryset)
        
        1. REST_FRAMEWORK = {'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend',],}
        2. DjangoFilterBackend 会根据 filterset_fields 去过滤 queryset
        3. DRF 会根据 ✅request.query_params [❌request.data] 自动生成过滤条件
        
        有多个筛选项时，会很方便
        filterset_fields = ('a', 'b', 'c',...)
        queryset = self.get_queryset()
        queryset = self.filter_queryset(queryset=queryset)
        
        OR
        
        if 'a' in request.query_params:
	        queryset = queryset.filter(a = request.query_params.get('a'))
        if 'b' in request.query_params:
	        queryset = queryset.filter(b = request.query_params.get('b'))
        ......
        
================================================================================================================   


"""