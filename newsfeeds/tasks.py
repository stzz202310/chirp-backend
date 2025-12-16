from celery import shared_task

from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed
from tweets.models import Tweet
from utils.time_constants import ONE_HOUR


@ shared_task(time_limit=ONE_HOUR)
def fanout_newsfeeds_task(tweet_id):
    # import 写在里面避免循环依赖
    from newsfeeds.services import NewsFeedService

    tweet = Tweet.objects.get(id=tweet_id)
    followers = FriendshipService.get_followers(user=tweet.user)
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
        NewsFeedService.push_newsfeed_to_cache(newsfeed=newsfeed)