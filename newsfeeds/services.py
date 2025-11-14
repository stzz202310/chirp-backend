from friendships.services import FriendshipService
from newsfeeds.models import NewsFeed

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