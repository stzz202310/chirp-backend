# settings.py 末尾有一行 `from twitter.local_settings import *`，
# 所以这个文件里的配置会覆盖 settings.py 里的同名配置。
# 我们用它来把所有 "127.0.0.1" 换成 docker-compose 里的服务名。
#
# 原理：docker-compose 会建一个内部网络，每个服务的「服务名」就是它的主机名。
# 容器里访问 mysql 不是访问 127.0.0.1，而是访问名为 "mysql" 的那个容器

DEBUG = True

# 容器里通过服务名互访，允许所有 host（开发环境）
ALLOWED_HOSTS = ['*']

# 数据库：HOST 从 127.0.0.1 改成服务名 "mysql"
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'twitter',
        'HOST': 'mysql',       # 对应 docker-compose 里的 mysql 服务
        'PORT': '3306',
        'USER': 'root',
        'PASSWORD': 'zhuzhu',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'memcached:11211',
        'TIMEOUT': 86400,
    },
    'testing': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'memcached:11211',
        'TIMEOUT': 86400,
        'KEY_PREFIX': 'testing',
    },
    'ratelimit': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': 'memcached:11211',
        'TIMEOUT': 86400 * 7,
        'KEY_PREFIX': 'rl',
    },
}

# Redis：HOST 改成服务名 "redis"
REDIS_HOST = 'redis'
REDIS_PORT = 6379

# Celery 的 broker 也指向 redis 服务（db 2，和 settings.py 里非测试环境一致）
CELERY_BROKER_URL = 'redis://redis:6379/2'

# HBase 在 Docker 环境中不启动，跳过所有 HBase 相关的 setUp/tearDown
HBASE_ENABLED = False
