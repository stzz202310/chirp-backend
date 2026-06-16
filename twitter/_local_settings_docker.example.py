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

# Memcached：HOST 改成服务名 "memcached"
#   之前 dev 用 LocMemCache 是为了绕开 "pymemcache 连接池并发响应错位"，
#   现已用 use_pooling=True 根治该问题，故 dev 切回真 memcached，与生产保持一致
#   (LocMemCache 是单进程内存、不共享、不走序列化，会掩盖 memcached 相关问题)
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

# Redis：HOST 改成服务名 "redis"
REDIS_HOST = 'redis'
REDIS_PORT = 6379

# Celery 的 broker 也指向 redis 服务（db 2，和 settings.py 里非测试环境一致）
CELERY_BROKER_URL = 'redis://redis:6379/2'

# HBase 在 Docker 环境中不启动，跳过所有 HBase 相关的 setUp/tearDown
HBASE_ENABLED = False

# 开发环境用本地文件存储，不走 S3
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
MEDIA_URL = '/media/'
