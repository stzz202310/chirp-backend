# chirp.conf:               告诉 Nginx"收到什么路径的请求，怎么处理"——转发给 Gunicorn、直接返回静态文件、还是托管 Django static
# docker-compose.prod.yml:  告诉 Docker"起哪些容器、用什么镜像、怎么启动、环境变量是什么"
# local_settings_prod.py:   告诉 Django"生产环境下用什么配置"——数据库连哪里、用哪个 storage、ALLOWED_HOSTS 是什么

import os

DEBUG = False  # 必须关闭，否则报错时会暴露代码细节

ALLOWED_HOSTS = [
    'chirp-app.dev',        # 域名
    'www.chirp-app.dev',    # www 域名
    '172.31.7.179',         # EC2 内网 IP: AWS VPC 内部地址，外网访问不到
    'localhost',
    '127.0.0.1',
]

# 生产用强密钥，从环境变量读
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-change-me-in-prod')

# 数据库：容器服务名
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'twitter',
        'HOST': 'mysql',
        'PORT': '3306',
        'USER': 'root',
        'PASSWORD': 'zhuzhu',
    }
}

# Memcached：容器服务名
_MEMCACHED_OPTIONS = {'use_pooling': True, 'ignore_exc': True}
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'memcached:11211',
        'TIMEOUT': 86400,
        'OPTIONS': _MEMCACHED_OPTIONS,
    },
    'testing': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'memcached:11211',
        'TIMEOUT': 86400,
        'KEY_PREFIX': 'testing',
        'OPTIONS': _MEMCACHED_OPTIONS,
    },
    'ratelimit': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'memcached:11211',
        'TIMEOUT': 86400 * 7,
        'KEY_PREFIX': 'rl',
        'OPTIONS': _MEMCACHED_OPTIONS,
    },
}

# Redis：容器服务名
REDIS_HOST = 'redis'
REDIS_PORT = 6379

# Celery broker
CELERY_BROKER_URL = 'redis://redis:6379/2'

# HBase 不启动
HBASE_ENABLED = False

# collectstatic 收集目录，Nginx 从这里读 Django admin 的 CSS/JS
STATIC_ROOT = '/app/staticfiles'
STATIC_URL = '/django-static/'  # 避免和前端 /static/ 冲突

# 告诉 Django 信任来自这个 IP 的 CSRF
CSRF_TRUSTED_ORIGINS = [
    'https://chirp-app.dev',
    'https://www.chirp-app.dev',
]

# urls: + static(XXX) 在生产环境下实际上是空操作—; DEBUG=False 时 Django 本身就不会处理这个路由
# 开发环境：文件存本地 → Django 的 /media/ 路由提供访问
# 生产环境：文件存 S3  → 浏览器直接访问 S3 URL，Django 完全不参与
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
