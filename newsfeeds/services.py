from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_helper import RedisHelper

class NewsFeedService(object):

    @classmethod
    def fanout_to_followers(cls, tweet):
        followers = FriendshipService.get_followers(tweet.user)
        # 错误的写法: for 循环 {Query 多次插入} 效率会非常低
        # web (client) <-> db (server) 数据传输和校验
        # for follower in followers:
        #     NewsFeed.objects.create(user=follower, tweet=tweet)

        # 正确的方法: 使用 bulk_create，会把 insert 语句合成一条
        # 多次 插入一条[错误] vs 一次 插入多条[正确]
        newsfeeds = [
            # 在调用 save() 之前，数据只存在于内存中，并未实际写入数据库。
            NewsFeed(user=follower, tweet=tweet)
            for follower in followers
        ]
        # 自己也能看到 自己发的帖子
        newsfeeds.append(NewsFeed(user=tweet.user, tweet=tweet))
        NewsFeed.objects.bulk_create(newsfeeds)
        # INSERT INTO `newsfeeds_newsfeed` (`user_id`, `tweet_id`, `created_at`)
        # VALUES
        # (1, 2, '2025-08-01 19:00:00.000000')
        # (2, 2, '2025-08-01 19:00:00.000000')
        # (3, 2, '2025-08-01 19:00:00.000000')

        # INSERT INTO `newsfeeds_newsfeed` (`user_id`, `tweet_id`, `created_at`) VALUES (1, 2, '2025-08-01 19:00:00.000000')
        # INSERT INTO `newsfeeds_newsfeed` (`user_id`, `tweet_id`, `created_at`) VALUES (2, 2, '2025-08-01 19:00:00.000000')
        # INSERT INTO `newsfeeds_newsfeed` (`user_id`, `tweet_id`, `created_at`) VALUES (3, 2, '2025-08-01 19:00:00.000000')

        # ⚠️ bulk create 不会触发 post_save 的 signal，所以需要手动 push 到 cache 里
        for newsfeed in newsfeeds:
            cls.push_newsfeed_to_cache(newsfeed=newsfeed)

    @classmethod
    def get_cached_newsfeeds(cls, user_id):
        queryset = NewsFeed.objects.filter(user_id=user_id).order_by('-created_at')
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        return RedisHelper.load_objects(key=key, queryset=queryset)

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        queryset = NewsFeed.objects.filter(user_id=newsfeed.user_id).order_by('-created_at')
        key = USER_NEWSFEEDS_PATTERN.format(user_id=newsfeed.user_id)
        RedisHelper.push_objects(key=key, obj=newsfeed, queryset=queryset)