from gatekeeper.models import GateKeeper
from newsfeeds.models import NewsFeed, HBaseNewsFeed
from newsfeeds.tasks import fanout_newsfeeds_main_task
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_helper import RedisHelper
from utils.redis_serializers import DjangoModelSerializer, HBaseModelSerializer


def lazy_load_newsfeeds(user_id):
     # lazy_load_objects = lazy_load_newsfeeds(user_id=1)   返回 _lazy_load, 通过闭包捕获 user_id=1
     # lazy_load_objects(limit=10)                          此时才真正执行 DB / HBase 查询
    def _lazy_load(limit):
        if GateKeeper.is_switch_on(gk_name='switch_newsfeed_to_hbase'):
            return HBaseNewsFeed.filter(prefix=(user_id,), limit=limit, reverse=True)
        return NewsFeed.objects.filter(user_id=user_id).order_by('-created_at')[:limit]
    return _lazy_load


class NewsFeedService(object):

    @classmethod
    def fanout_to_followers(cls, tweet):
        # .delay() 将任务放入 Celery message queue，立刻返回，不阻塞用户发帖流程
        # 任意一个监听 message queue 的 worker 进程异步消费并执行 fanout 逻辑

        # delay 参数只传可被 Celery 序列化的基本类型 int / str / list (worker 是独立进程，甚至在不同机器上)
        # 传 tweet.id (int) ✅   传 tweet 对象 ❌ (Celery 不知道如何序列化 Tweet)
        created_at = cls.created_at(tweet=tweet)
        fanout_newsfeeds_main_task.delay(tweet_id=tweet.id, created_at=created_at, tweet_user_id=tweet.user_id)

    @classmethod
    def get_cached_newsfeeds(cls, user_id):
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        if GateKeeper.is_switch_on(gk_name='switch_newsfeed_to_hbase'):
            serializer = HBaseModelSerializer
        else:
            serializer = DjangoModelSerializer
        return RedisHelper.load_objects(
            key=key,
            lazy_load_objects=lazy_load_newsfeeds(user_id=user_id),
            serializer=serializer,
        )

    @classmethod
    def push_newsfeed_to_cache(cls, newsfeed):
        user_id = newsfeed.user_id
        key = USER_NEWSFEEDS_PATTERN.format(user_id=user_id)
        RedisHelper.push_objects(
            key=key,
            obj=newsfeed,
            lazy_load_objects=lazy_load_newsfeeds(user_id=user_id),
        )

    @classmethod
    def create(cls, **kwargs):
        if GateKeeper.is_switch_on(gk_name='switch_newsfeed_to_hbase'):
            newsfeed = HBaseNewsFeed.create(**kwargs)
            # ⚠️ HBase 不走 Django ORM，post_save signal 不触发，需手动更新缓存
            cls.push_newsfeed_to_cache(newsfeed=newsfeed)
        else:
            newsfeed = NewsFeed.objects.create(**kwargs)
        return newsfeed

    @classmethod
    def batch_create(cls, batch_params):
        if GateKeeper.is_switch_on(gk_name='switch_newsfeed_to_hbase'):
            newsfeeds = HBaseNewsFeed.batch_create(batch_data=batch_params)
        else:
            newsfeeds = [NewsFeed(**params) for params in batch_params]
            NewsFeed.objects.bulk_create(objs=newsfeeds)

        # ⚠️ bulk_create / HBase 均不触发 post_save signal，需手动更新缓存
        for newsfeed in newsfeeds:
            NewsFeedService.push_newsfeed_to_cache(newsfeed=newsfeed)
        return newsfeeds

    @classmethod
    def count(cls, user_id=None):
        # for unit test only
        if GateKeeper.is_switch_on(gk_name='switch_newsfeed_to_hbase'):
            return len(HBaseNewsFeed.filter(prefix=(user_id,)))

        if user_id is None:
            return NewsFeed.objects.count()
        return NewsFeed.objects.filter(user_id=user_id).count()

    @classmethod
    def created_at(cls, tweet):
        if GateKeeper.is_switch_on(gk_name='switch_newsfeed_to_hbase'):
             return tweet.timestamp
        return tweet.created_at