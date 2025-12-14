from utils.listeners import invalidate_object_cache


def incr_comments_count(sender, instance, created, **kwargs):
    from django.db.models import F
    from tweets.models import Tweet

    if not created:
        return

    # handle new comment
    Tweet.objects.filter(id=instance.tweet_id).update(comments_count=F('comments_count') + 1)
    # invalidate_object_cache(sender=Tweet, instance=instance.tweet)


def decr_comments_count(sender, instance, **kwargs):
    from django.db.models import F
    from tweets.models import Tweet

    # handle comment deletion
    Tweet.objects.filter(id=instance.tweet_id)\
        .update(comments_count=F('comments_count') - 1)
    # invalidate_object_cache(sender=Tweet, instance=instance.tweet)