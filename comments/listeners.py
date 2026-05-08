from utils.redis_helper import RedisHelper


def incr_comments_count(sender, instance, created, **kwargs):
    from django.db.models import F
    from tweets.models import Tweet

    if not created: # 更新评论时不应增加 comments_count
        return

    Tweet.objects.filter(id=instance.tweet_id).update(comments_count=F('comments_count') + 1)
    RedisHelper.incr_count(obj=instance.tweet, attr='comments_count')

def decr_comments_count(sender, instance, **kwargs):
    from django.db.models import F
    from tweets.models import Tweet

    Tweet.objects.filter(id=instance.tweet_id).update(comments_count=F('comments_count') - 1)
    RedisHelper.decr_count(obj=instance.tweet, attr='comments_count')