def push_tweet_to_cache(sender, instance, created, **kwargs):
    if not created:
        """
        当前: tweet 没有提供修改的接口
        
        假设: tweet 提供了修改的接口 TODO [HARD]
        方法1: 修改 tweet => redis:     clear cache, load from DB
        
        方法2: 修改 tweet => memcached: clear cache, load from DB
        memcached   {tweet_id: tweet instance} 
        redis       {user_id : 这个用户发的帖子的ids}
        
        redis       tweet_ids = [10, 9, 8, 7, 6]
        memcached   cache.get_many([...]), if cache miss, load from DB
        DB          Tweet.objects.filter(tweet_id__in=[8, 7])
        """
        return

    from tweets.services import TweetService
    TweetService.push_tweet_to_cache(tweet=instance)