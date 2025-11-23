print(0)


"""
config.vm.network "forwarded_port", guest: 8000, host: 80
Guest VM 内部的 8000 端口 → 被映射到 Host 宿主机的 80 端口

config.vm.network "private_network", ip: "192.168.33.10"
宿主机可以直接访问虚拟机 IP 为 192.168.33.10，端口不变

python manage.py runserver 0.0.0.0:8000
它监听的是 虚拟机内部 的 8000 端口

✅ 结论：宿主机能访问：
| 访问方式                        | 是否成功 | 原因                            |
| --------------------------- | ---- | ----------------------------------- |
| `http://localhost:80`       | ✅    | host:80 → forwarded to guest:8000  |
| `http://127.0.0.1:80`       | ✅    | 同上                                |
| `http://192.168.33.10:8000` | ✅    | 直连虚拟机私网 IP + 真实 8000 端口     |

❌ 宿主机不能访问：
| 访问方式                      | 是否成功 | 原因                          |
| ------------------------- | ---- | -------------------------------    |
| `http://localhost:8000`   | ❌    | 宿主机上并没有进程监听 8000          |
| `http://127.0.0.1:8000`   | ❌    | 同上                              |
| `http://192.168.33.10:80` | ❌    | 80 并没有映射回去，也没有在 VM 上监听 |


python manage.py runserver [127.0.0.1:8000]
只监听本机回环地址, 只有虚拟机内部能访问

| 访问者                                       | 是否能访问  | 原因                         |
| ------------------------------------------- | --------- | ---------------------------- |
| 虚拟机内部自己访问 `http://127.0.0.1:8000`     | ✅ 可以   | 本机访问本机                   |
| 宿主机访问 `localhost:8000`|`127.0.0.1:8000` | ❌ 不行    | 宿主机和虚拟机是两个不同的“本机”  |
| 宿主机访问 `192.168.33.10:8000`              | ❌ 不行    | Django 没监听虚拟机的对外网络接口 |

================================================================================================================

@action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
detail=True 的 actions 会默认先去调用 get_object() {get_object_or_404()} 也就是
queryset.filter(pk=1) 查询一下这个 object 在不在

================================================================================================================

排序 [不会对数据库产生影响，只会影响 QuerySet]
1. class Tweet(models.Model): class Meta: ordering = ('-created_at',)       不推荐，潜规则
2. tweets = Tweet.objects.filter(user_id=user_id).order_by('-created_at')   推荐，明显直观 [2会覆盖1]

================================================================================================================

from_user       模型字段名|外键字段      接收 User 对象
from_user_id    数据库列               接收用户 ID（整数）

⚠️ 对象 → 用 from_user
⚠️ ID  → 用 from_user_id

⚠️ 模型索引/约束（index_together, UniqueConstraint）必须写 from_user（模型字段名）

1 Serializer 决定 validated_data 是 "对象" 还是 "ID"

2 查询中可以灵活使用 from_user 或 from_user_id
    Friendship.objects.filter(from_user=user_obj)      # 传对象
    Friendship.objects.filter(from_user_id=user_id)    # 传 ID

================================================================================================================

(1) 更改 models
(2) makemigrations   ← 让迁移文件跟上你的代码
(3) test             ← 使用包含 {最新迁移文件} 的测试数据库
(4) 如果有问题 再次修改 ← 重复1-3
(5) migrate          ← 应用到正式数据库


"""