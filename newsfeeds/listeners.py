def push_newsfeed_to_cache(sender, instance, created, **kwargs):
    if not created:
        return
    """
    TODO [Myself] 用户A的关注列表更新后，如何获取用户A的newsfeeds?
    1. A 关注了 B
    2. B 发了 tweet1 [newsfeeds: user=A, tweet=tweet1, created_at=...]
    3. A 取关了 B
    方法1: 取关时，直接更新newsfeed表单 [is_deleted=True]
    方法2: 获取A的新鲜事列表，删除其中[已取关用户发的帖子]
    """

    from newsfeeds.services import NewsFeedService
    NewsFeedService.push_newsfeed_to_cache(newsfeed=instance)