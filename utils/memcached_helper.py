from django.conf import settings
from django.core.cache import caches

cache = caches['testing'] if settings.TESTING else caches['default']


class MemcachedHelper:

    @classmethod
    def get_key(cls, model_class, object_id):
        return f'{model_class.__name__.lower()}:{object_id}'

    @classmethod
    def get_object_through_cache(cls, model_class, object_id):
        key = cls.get_key(model_class=model_class, object_id=object_id)
        # 1. read from cache first
        #    key 如果不存在, return None 不会报错
        obj = cache.get(key)
        if obj: # cache hit
            return obj

        # 2. cache miss, read from database
        obj = model_class.objects.get(pk=object_id)
        cache.set(key, obj)
        return obj

    @classmethod
    def invalidate_cached_object(cls, model_class, object_id):
        key = cls.get_key(model_class=model_class, object_id=object_id)
        cache.delete(key)