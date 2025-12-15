from utils.redis_helper import RedisHelper


def incr_likes_count(sender, instance, created, **kwargs):
    from django.db.models import F
    from tweets.models import Tweet

    if not created:
        return

    # like.content_type.model_class()   Tweet OR Comment
    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        # TODO [HOMEWORK] 给 Comment 使用类似的方法进行 likes_count 的统计
        return

    """
    ❌ 不可以使用 [因为这个操作不是原子操作: 会导致明星帖子的点赞数 容易出错]
    tweet = instance.content_object
    tweet.likes_count += 1 [save() 之前又有人点赞，数据就错了]
    tweet.save()
    
    Tweet.objects.filter(pk=tweet.id).update(likes_count=tweet.likes_count + 1)
    假设 tweet.likes_count = 10
    ❌ SQL Query: UPDATE tweets_tweet SET likes_count = 11 WHERE id=<instance.object_id>;
    ✅ SQL Query: UPDATE tweets_tweet SET likes_count = likes_count + 1 WHERE id=<instance.object_id>;
    
    
    | 特性 / 场景     | `save()`                   | `update()`                       |
    | ---------------| -------------------------- | -------------------------------- |
    | 作用对象         | 单个模型实例                | QuerySet 或多条记录                |
    | SQL            | `INSERT`|`UPDATE`(ORM 层)  | 直接 `UPDATE`                     |
    | 触发 signal     | ✅ pre_save| post_save    | ❌ 不触发                         |
    | ORM 校验|hooks  | ✅ 会触发                  | ❌ 不触发                         |
    | 性能            | 较慢                       | 快（直接 SQL）                     |
    | 并发安全         | ❌ 不安全（如计数器）        | ✅ 安全（配合 F() 原子操作）        |
    | 对 cache 影响    | ✅ signal 可用来刷新 cache | ❌ 需要显式 cache.delete() 或更新  |
    | 语义            | “这个对象被修改了”           | “数据库字段被校准 / 更新”            |

    方法 1: QuerySet.update() ❌ 不会触发任何 model signal          
    Tweet.objects.filter(pk=instance.object_id).update(likes_count=F('likes_count') + 1)
    
    方法 2: instance.save()   ✅ 触发 pre_save / post_save   [不推荐]
    tweet = instance.content_object
    tweet.likes_count = F('likes_count') + 1
    tweet.save()
    
    tweet.likes_count         现在是一个 F() 表达式，不是 int
    print(tweet.likes_count)  输出: <CombinedExpression: F(likes_count) + Value(1)>
    """
    Tweet.objects.filter(pk=instance.object_id).update(likes_count=F('likes_count') + 1)
    # ❌ 缓存未更新，obj未更新，✅ 数据库更新了
    # ❌ 不会触发任何的 model signal, 所以 redis{user_id:[tweets]}, memcached{tweet_id:tweet_obj} 不会更新
    # ❌ 不推荐通过触发 model signal, 删除缓存; 否则每次点赞|取消赞，都会删除tweet缓存 => cache miss => read from DB
    # ✅ 把 likes_count[仅有+1和-1操作] 分离出来，单独保存在 cache 中
    tweet = instance.content_object
    RedisHelper.incr_count(obj=tweet, attr='likes_count')
    # ✅ 数据库更新        Tweet.objects.filter().update(F)
    # ✅ 缓存更新, obj更新 RedisHelper.incr_count


def decr_likes_count(sender, instance, **kwargs):
    from django.db.models import F
    from tweets.models import Tweet

    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        # TODO [HOMEWORK] 给 Comment 使用类似的方法进行 likes_count 的统计
        return

    # handle tweet likes cancel
    Tweet.objects.filter(pk=instance.object_id).update(likes_count=F('likes_count') - 1)
    RedisHelper.decr_count(obj=instance.content_object, attr='likes_count')