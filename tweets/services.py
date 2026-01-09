from tweets.models import Tweet, TweetPhoto
from twitter.cache import USER_TWEETS_PATTERN
from utils.redis_helper import RedisHelper


def lazy_load_tweets(user_id):
    def _lazy_load(limit):
        return Tweet.objects.filter(user_id=user_id).order_by('-created_at')[:limit]
    return _lazy_load


class TweetService(object):

    @classmethod
    def create_photos_from_files(cls, tweet, files):
        photos = []
        for index, file in enumerate(files):
            photo = TweetPhoto(
                tweet=tweet,
                user=tweet.user,
                file=file,
                order=index,
            )
            photos.append(photo)
        TweetPhoto.objects.bulk_create(objs=photos)

    @classmethod
    def get_cached_tweets(cls, user_id):
        # ⚠️ queryset is lazy loading 懒惰加载
        key = USER_TWEETS_PATTERN.format(user_id=user_id)
        return RedisHelper.load_objects(
            key=key,
            lazy_load_objects=lazy_load_tweets(user_id=user_id),
            # DjangoModelSerializer
        )

    @classmethod
    def push_tweet_to_cache(cls, tweet):
        # ⚠️ queryset is lazy loading 懒惰加载
        user_id = tweet.user_id
        key = USER_TWEETS_PATTERN.format(user_id=user_id)
        RedisHelper.push_objects(
            key=key,
            obj=tweet,
            lazy_load_objects=lazy_load_tweets(user_id=user_id),
        )