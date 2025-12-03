DEBUG = True

# checkout https://www.neilwithdata.com/django-sql-logging
LOGGING = {
    'version': 1,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',   # DEBUG -> INFO
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'INFO',    # DEBUG -> INFO
            'handlers': ['console'],
            'propagate': False,  # 不向上冒泡, 避免重复输出
        },
    },
}