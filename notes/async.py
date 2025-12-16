"""""""""
webserver1  webserver2  x 5000 [20:1]   可以访问数据库     webserver: django

Message Queue [按照一定规则将任务分配给 "其中一个" worker]    CELERY_BROKER_URL = 'redis://127.0.0.1:6379/2'

worker1     worker2     x 200 [监听 MQ]  可以访问数据库     worker: celery -A twitter worker -l info

1. 用户A发了一个帖子
2. webserver 创建了一个任务 放在 MQ 中, 并通知用户A帖子创建成功
3. MQ 将这个任务分配给 某个 worker
4. worker 执行 fanout [写入数据库 newsfeeds_newsfeed table]
5. 用户A的粉丝查看新鲜事列表，webserver 从数据库拿到数据并展示

=======================================================================================

mysqlclient: python 和 MQ    之间沟通的桥梁
celery     : python 和 MySQL 之间沟通的桥梁 [broker: redis]

send_email.delay(user_id=1)

1. CELERY_TASK_ALWAYS_EAGER = False [Async Task 异步任务, 需要 broker 和 worker]
Django request
  ↓
serialize task
  ↓
send to Redis (broker, MQ)
  ↓
Celery worker 拉取
  ↓
执行 task

2. CELERY_TASK_ALWAYS_EAGER = True [同步 立刻执行, 不依赖 Redis, 不需要 worker]
Django request
  ↓
直接执行 send_email()
  ↓
返回结果

result = add.delay(1, 2)
print(result.get())
eager=True  → 立刻返回 3
eager=False → 阻塞等 worker

=======================================================================================

1. eager 执行: 不进队列、不走 worker, 包括两种情况:
task.apply()        # 手动同步执行
task.delay()        # 但设置了 task_always_eager = True

2. CELERY_TASK_EAGER_PROPAGATES = False [默认情况]
result = task.apply()
如果 task 里报错, Celery 捕获异常, 把异常存到 result.traceback [不往外抛], request 200

3. CELERY_TASK_EAGER_PROPAGATES = True
task.apply(throw=True)
像普通 Python 函数一样, 让异常沿着调用栈冒泡, request 500

4. 默认情况: False
Celery 是一个 异步系统, 默认假设 [task 崩了 ≠ request 崩了], 所以 [异常默认被隔离]

@shared_task
def divide(a, b):
    return a / b

divide.delay(1, 0)
print("继续执行")

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = False
结果: 继续执行 ⚠️ 实际上 task 已经 ZeroDivisionError 了, 只是被 Celery 吞掉了

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
结果: ZeroDivisionError: division by zero

=======================================================================================

明星发帖 =request=> webserver ==> db [fanout]   10s 后, fanout 完成
发帖完成 <=response=

明星发帖 =request=> webserver ==> db [把这个帖子写入 tweet 表单] 
发帖完成 <=response=          ==> MQ [创建1个异步任务] ==> worker x 1 ==> db   fanout时间: 10s
发帖完成 <=response=          ==> MQ [创建n个异步任务] ==> worker x n ==> db   fanout时间: {10/n}s

1. 单个任务执行时间过长的潜在风险: 任务中途出错，数据库连接超时
2. 使用分布式系统，把任务批量化 [100个workers, 每个worker 20个子进程, 并发能力=2000]

=======================================================================================
    
default 队列   fanout_newsfeeds_main_task + fanout_newsfeeds_batch_task
明星发帖后，default 队列 把任务批量化分配给 default 队列
default 队列 会被批量化的 fanout newsfeeds 任务占据，新的任务(用户注册验证)只能排在后面 等待被执行

default 队列   fanout_newsfeeds_main_task
newsfeeds 队列 fanout_newsfeeds_batch_task
明星发帖后，default 队列 把任务批量化分配给 newsfeeds 队列
newsfeeds 队列 批量化的 fanout newsfeeds 任务
default   队列 可以继续接收 新的任务

"""