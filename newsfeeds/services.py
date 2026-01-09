from gatekeeper.models import GateKeeper
from newsfeeds.models import NewsFeed, HBaseNewsFeed
from newsfeeds.tasks import fanout_newsfeeds_main_task
from twitter.cache import USER_NEWSFEEDS_PATTERN
from utils.redis_helper import RedisHelper
from utils.redis_serializers import DjangoModelSerializer, HBaseModelSerializer


def lazy_load_newsfeeds(user_id):
    """""""""
    返回一个延迟加载（lazy load）的 newsfeed 读取函数。
    
    该函数本身不会触发任何数据库 / HBase 查询，
    只有在调用返回的函数并传入 limit 时，才会真正执行查询。
    
    使用示例:
        lazy_load_func = lazy_load_newsfeeds(user_id=1)
        # lazy_load_func 即内部的 _lazy_load，已通过闭包捕获 user_id
        newsfeeds = lazy_load_func(limit=100)
        # 此时才真正执行 DB / HBase 查询
    """
    def _lazy_load(limit):
        if GateKeeper.is_switch_on(gk_name='switch_newsfeed_to_hbase'):
            return HBaseNewsFeed.filter(prefix=(user_id,), limit=limit, reverse=True)
        return NewsFeed.objects.filter(user_id=user_id).order_by('-created_at')[:limit]
    return _lazy_load


class NewsFeedService(object):

    @classmethod
    def fanout_to_followers(cls, tweet):
        # 这句话的作用是，在 celery 配置的 message queue 中创建一个 fanout 的任务[参数是tweet]
        # 任意一个在监听 message queue 的 worker 进程都有机会拿到这个任务。
        # worker 进程中会执行 fanout_newsfeeds_task 里的代码来实现一个异步的任务处理
        # 如果这个任务需要处理 10s，则这 10s 会花费在 worker 进程上，而不是花费在用户发帖的过程中。
        # 所以这里 .delay 操作会[立刻执行 立刻结束] 从而不影响用户的正常操作。
        # (因为这里只是创建了一个任务，把任务信息放在了 message queue 里，并没有真正执行这个任务)

        # 要注意的是，delay 里的参数必须是可以被 celery serialize 的值，因为 worker 进程是一个
        # 独立的进程，甚至在不同的机器上，没有办法知道当前 web 进程的某片内存空间里的值是什么。
        # 所以 我们只能把 ⚠️tweet.id 作为参数传进去，而不能把 tweet 传进去。
        # 因为 celery 并不知道如何 serialize Tweet
        created_at = cls.created_at(tweet=tweet)
        fanout_newsfeeds_main_task.delay(tweet_id=tweet.id, created_at=created_at, tweet_user_id=tweet.user_id)
        # fanout_newsfeeds_main_task.apply_async(
        #     kwargs={'tweet_id': tweet.id, 'tweet_user_id': tweet.user_id},
        #     queue='default',
        #     routing_key='default',  # 可省略，queue 已经决定
        # )

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
            # ⚠️ 需要手动触发 cache 更改，因为没有 listener 监听 hbase create
            cls.push_newsfeed_to_cache(newsfeed=newsfeed)
        else:
            newsfeed = NewsFeed.objects.create(**kwargs)
        return newsfeed

    @classmethod
    def batch_create(cls, batch_params):
        if GateKeeper.is_switch_on(gk_name='switch_newsfeed_to_hbase'):
            newsfeeds = HBaseNewsFeed.batch_create(batch_data=batch_params)
        else:
            # 错误的写法: for 循环 {数据库操作} 效率会非常低
            # web (client) <==> db (server) 数据传输和校验
            # for follower_id in follower_ids:
            #     NewsFeed.objects.create(user_id=follower_id, tweet_id=tweet_id)

            # 正确的方法: 使用 bulk_create，会把 insert 语句合成一条
            # 多次 插入一条[错误] vs 一次 插入多条[正确]
            # INSERT INTO `newsfeeds_newsfeed` (`user_id`, `tweet_id`, `created_at`)
            # VALUES
            # (1, 2, '2025-08-01 19:00:00.000000')
            # (2, 2, '2025-08-01 19:00:00.000000')
            # (3, 2, '2025-08-01 19:00:00.000000')

            # INSERT INTO `newsfeeds_newsfeed` (`user_id`, `tweet_id`, `created_at`) VALUES (1, 2, '...')
            # INSERT INTO `newsfeeds_newsfeed` (`user_id`, `tweet_id`, `created_at`) VALUES (2, 2, '...')
            # INSERT INTO `newsfeeds_newsfeed` (`user_id`, `tweet_id`, `created_at`) VALUES (3, 2, '...')
            newsfeeds = [NewsFeed(**params) for params in batch_params]
            # 在调用 save() 之前，数据只存在于内存中，并未实际写入数据库
            NewsFeed.objects.bulk_create(objs=newsfeeds)

        # ⚠️ bulk create 不会触发 post_save 的 signal，所以需要手动 push 到 cache 里
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
             return tweet.timestamp # HBase: int
        return tweet.created_at     # MySQL: iso