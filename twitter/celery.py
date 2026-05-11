import os

from celery import Celery

# 1. 指定 Django settings (让 Celery 能使用 Django)
# 否则在 task 中使用 ORM / settings / cache 会报错（Django 未初始化）
# ORM: Tweet.objects.create(...)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twitter.settings')

# 2. 创建 Celery 应用实例
# 'twitter': 应用名 (也是 worker 名字前缀)
app = Celery('twitter')

# 3. 从 Django settings 加载 Celery 配置
# 只读取以 CELERY_ 开头的配置，例如: CELERY_BROKER_URL
app.config_from_object('django.conf:settings', namespace='CELERY')

# 4. 自动发现各 app 里的 task: 让 Celery 自动去每个 Django app 里找 tasks.py
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
"""
这是一个 官方示例调试任务
@app.task   把函数注册成 Celery task, worker 能执行它
bind=True   可以通过 self 访问任务上下文 (如 request.id, retries 等)
ignore_result=True  不把 task 执行结果存到 result backend, 减少 Redis / DB 压力

celery -A twitter worker -l info

from twitter.celery import debug_task
debug_task.delay()  # <AsyncResult: d1477fa6-b59d-4fe6-aa69-8228a01c0501>
"""