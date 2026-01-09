from celery import shared_task

from friendships.services import FriendshipService
from newsfeeds.constants import FANOUT_BATCH_SIZE
from utils.time_constants import ONE_HOUR


@shared_task(bind=True, routing_key='newsfeeds', time_limit=ONE_HOUR)
def fanout_newsfeeds_batch_task(self, tweet_id, created_at, follower_ids):
    # 打印当前任务队列信息
    # print("Batch task executing on queue:", getattr(self.request, "delivery_info", {}))

    # import 写在里面避免循环依赖
    from newsfeeds.services import NewsFeedService
    batch_params = [
        {'user_id': follower_id, 'created_at': created_at, 'tweet_id': tweet_id}
        for follower_id in follower_ids
    ]
    newsfeeds = NewsFeedService.batch_create(batch_params=batch_params)
    return f'{len(newsfeeds)} newsfeeds created.'


@shared_task(bind=True, routing_key='default', time_limit=ONE_HOUR)
def fanout_newsfeeds_main_task(self, tweet_id, created_at, tweet_user_id):
    # 打印当前任务队列信息
    # print("Main task executing on queue:", getattr(self.request, "delivery_info", {}))

    from newsfeeds.services import NewsFeedService
    # 将推给自己的 Newsfeed 率先创建，确保自己能最快看到
    NewsFeedService.create(
        user_id=tweet_user_id,
        tweet_id=tweet_id,
        created_at=created_at,
    )

    # 获得所有的 follower ids, 按照 batch size 拆分开
    follower_ids = FriendshipService.get_follower_user_id_list(to_user_id=tweet_user_id)
    index = 0
    while index < len(follower_ids):
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        fanout_newsfeeds_batch_task.delay(
            tweet_id=tweet_id,
            created_at=created_at,
            follower_ids=batch_ids,
        )
        # fanout_newsfeeds_batch_task.apply_async(
        #     kwargs={'tweet_id': tweet_id, 'follower_ids': batch_ids},
        #     queue='newsfeeds',
        #     routing_key='newsfeeds',  # 可省略，queue 已经决定
        # )
        index += FANOUT_BATCH_SIZE

    batch_count = (len(follower_ids) - 1) // FANOUT_BATCH_SIZE + 1
    return f'{len(follower_ids)} newsfeeds going to fanout, {batch_count} batches created.'