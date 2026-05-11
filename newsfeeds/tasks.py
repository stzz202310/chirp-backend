from celery import shared_task
from dateutil import parser

from friendships.services import FriendshipService
from newsfeeds.constants import FANOUT_BATCH_SIZE
from utils.time_constants import ONE_HOUR


@shared_task(bind=True, routing_key='newsfeeds', time_limit=ONE_HOUR)
def fanout_newsfeeds_batch_task(self, tweet_id, created_at, follower_ids):
    # 打印当前任务队列信息
    # print("Batch task executing on queue:", getattr(self.request, "delivery_info", {}))
    if isinstance(created_at, str):
        created_at = parser.isoparse(created_at)

    from newsfeeds.services import NewsFeedService
    batch_params = [
        {'user_id': follower_id, 'created_at': created_at, 'tweet_id': tweet_id}
        for follower_id in follower_ids
    ]
    newsfeeds = NewsFeedService.batch_create(batch_params=batch_params)
    return f'{len(newsfeeds)} newsfeeds created.'


@shared_task(bind=True, routing_key='default', time_limit=ONE_HOUR)
def fanout_newsfeeds_main_task(self, tweet_id, created_at, tweet_user_id):
    # ⚠️ Celery .delay() 会将 datetime 序列化为字符串, task 接收时需还原
    # MySQL: datetime → 字符串 → 还原为 datetime
    # HBase: int(timestamp) 不受影响
    if isinstance(created_at, str):
        created_at = parser.isoparse(created_at)

    from newsfeeds.services import NewsFeedService
    # 1. 优先为发帖人自己创建 NewsFeed，确保第一时间看到自己的帖子
    NewsFeedService.create(
        user_id=tweet_user_id,
        tweet_id=tweet_id,
        created_at=created_at,
    )

    # 2. 获取所有粉丝 id，按 FANOUT_BATCH_SIZE 分批
    follower_ids = FriendshipService.get_follower_user_id_list(to_user_id=tweet_user_id)
    index = 0
    while index < len(follower_ids):
        # 3. 每批派发一个 fanout_newsfeeds_batch_task 异步任务
        batch_ids = follower_ids[index: index + FANOUT_BATCH_SIZE]
        fanout_newsfeeds_batch_task.delay(
            tweet_id=tweet_id,
            created_at=created_at,
            follower_ids=batch_ids,
        )
        index += FANOUT_BATCH_SIZE

    batch_count = (len(follower_ids) - 1) // FANOUT_BATCH_SIZE + 1
    return f'{len(follower_ids)} newsfeeds going to fanout, {batch_count} batches created.'