from utils.redis_helper import RedisHelper


def incr_likes_count(sender, instance, created, **kwargs):
    # 1. Like 表 已经更新, 触发 post_save signal
    from django.db.models import F
    from tweets.models import Tweet

    if not created:
        return

    # like.content_type.model_class(): Tweet OR Comment
    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        # TODO [Homework] 增加 Comment.likes_count, 类似 Tweet.likes_count
        return

    # 2. 更新 Tweet 表 likes_count (F() 表达式, 原子操作, 不触发 post_save signal)
    Tweet.objects.filter(pk=instance.object_id).update(likes_count=F('likes_count') + 1)
    # 3. 同步 Redis 计数
    RedisHelper.incr_count(obj=instance.content_object, attr='likes_count')


def decr_likes_count(sender, instance, **kwargs):
    from django.db.models import F
    from tweets.models import Tweet

    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        # TODO [Homework] 增加 Comment.likes_count, 类似 Tweet.likes_count
        return

    Tweet.objects.filter(pk=instance.object_id).update(likes_count=F('likes_count') - 1)
    RedisHelper.decr_count(obj=instance.content_object, attr='likes_count')