from celery import shared_task

from friendships.services import FriendshipService
from newsfeeds.constants import FANOUT_BATCH_SIZE
from newsfeeds.models import NewsFeed
from utils.time_constants import ONE_HOUR


@shared_task(bind=True, routing_key='newsfeeds', time_limit=ONE_HOUR)
def fanout_newsfeeds_batch_task(self, tweet_id, follower_ids):
    # 打印当前任务队列信息
    # print("Batch task executing on queue:", getattr(self.request, "delivery_info", {}))

    # import 写在里面避免循环依赖
    from newsfeeds.services import NewsFeedService

    # 错误的写法: for 循环 {数据库操作} 效率会非常低
    # web (client) <-> db (server) 数据传输和校验
    # for follower_id in follower_ids:
    #     NewsFeed.objects.create(user_id=follower_id, tweet_id=tweet_id)

    # 正确的方法: 使用 bulk_create，会把 insert 语句合成一条
    # 多次 插入一条[错误] vs 一次 插入多条[正确]
    newsfeeds = [
        # 在调用 save() 之前，数据只存在于内存中，并未实际写入数据库。
        NewsFeed(user_id=follower_id, tweet_id=tweet_id)
        for follower_id in follower_ids
    ]

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

    return f'{len(newsfeeds)} newsfeeds created.'


@shared_task(bind=True, routing_key='default', time_limit=ONE_HOUR)
def fanout_newsfeeds_main_task(self, tweet_id, tweet_user_id):
    # 打印当前任务队列信息
    # print("Main task executing on queue:", getattr(self.request, "delivery_info", {}))

    # 将推给自己的 Newsfeed 率先创建，确保自己能最快看到
    NewsFeed.objects.create(user_id=tweet_user_id, tweet_id=tweet_id)

    # 获得所有的 follower ids, 按照 batch size 拆分开
    follower_ids = FriendshipService.get_follower_ids(to_user_id=tweet_user_id)
    index = 0
    while index < len(follower_ids):
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        fanout_newsfeeds_batch_task.delay(tweet_id=tweet_id, follower_ids=batch_ids)
        # fanout_newsfeeds_batch_task.apply_async(
        #     kwargs={'tweet_id': tweet_id, 'follower_ids': batch_ids},
        #     queue='newsfeeds',
        #     routing_key='newsfeeds',  # 可省略，queue 已经决定
        # )
        index += FANOUT_BATCH_SIZE

    batch_count = (len(follower_ids) - 1) // FANOUT_BATCH_SIZE + 1
    return f'{len(follower_ids)} newsfeeds going to fanout, {batch_count} batches created.'