from utils.redis_helper import RedisHelper


def incr_likes_count(sender, instance, created, **kwargs):
    from django.db.models import F
    from tweets.models import Tweet

    if not created:
        return

    # like.content_type.model_class(): Tweet OR Comment
    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        # TODO [Homework] 增加 Comment.likes_count, 类似 Tweet.likes_count
        return

    Tweet.objects.filter(pk=instance.object_id).update(likes_count=F('likes_count') + 1)
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