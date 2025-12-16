import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'twitter.settings')
# 1. 告诉 Celery：用哪个 Django settings
#    Celery task 里, 会用 Django ORM, cache, settings]

app = Celery('twitter') # celery -A twitter worker
# 2. 创建 Celery 应用实例 ['twitter': 应用名, worker 名字前缀, queue / log 的命名空间]

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')
# 3. 从 Django settings 加载 Celery 配置
#    从 settings.py 里读配置 + 只读以 CELERY_ 开头的配置

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
# 4. 自动发现各 app 里的 task: 让 Celery 自动去每个 Django app 里找 tasks.py
#    app 在 INSTALLED_APPS + 文件名叫 tasks.py
#    tweets/tasks.py, likes/tasks.py


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
"""
这是一个 官方示例用的调试 task
@app.task   把函数注册成 Celery task, worker 能执行它
bind=True   把 task 实例本身作为第一个参数; self.request 包含 task id, args|kwargs, retries
ignore_result=True  不把 task 执行结果存到 result backend, 减少 Redis / DB 压力

celery -A twitter worker -l info [-c 4]

from twitter.celery import debug_task
debug_task.delay()  # <AsyncResult: d1477fa6-b59d-4fe6-aa69-8228a01c0501>
"""