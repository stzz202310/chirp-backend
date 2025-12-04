from friendships.models import Friendship


class FriendshipService(object):

    @classmethod
    def get_followers(cls, user):
        # 错误的写法一：会导致 N + 1 Queries 的问题;
        # 1 Query: filter 出所有 friendships
        # N Query: for 循环每个 friendship 取 from_user
        # friendships = Friendship.objects.filter(to_user=user)
        # return [friendship.from_user for friendship in friendships]

        # 错误的写法二
        # 这种写法是使用了 JOIN 操作，让 friendship table 和 user table 在 from_user
        # 这个属性上 join 了起来。join 操作在大规模用户的 web 场景下是禁用的，因为非常慢。
        # friendships = Friendship.objects.filter(
        #     to_user=user
        # ).select_related('from_user')
        # return [friendship.from_user for friendship in friendships]

        # SELECT * FROM `friendships_friendship`
        # INNER JOIN `auth_user`
        # ON "friendships_friendship"."from_user_id" = "auth_user"."id"
        # WHERE friendships_friendship"."to_user_id" = <user.id>;
        # ========================================================================

        # 正确的写法一，自己手动 filter id，使用 IN Query 查询
        # friendships = Friendship.objects.filter(to_user=user)
        # follower_ids = [friendship.from_user_id for friendship in friendships]
        # followers = User.objects.filter(id__in=follower_ids)

        # 正确的写法二，使用 prefetch_related，会自动执行成两条语句，用 In Query 查询
        # 实际执行的 SQL 查询和上面是一样的，一共两条 SQL Queries
        # 1. SELECT * FROM `friendships_friendship`
        #    WHERE `friendships_friendship`.`to_user_id` = <user.id>;
        # 2. SELECT * FROM `auth_user` WHERE `auth_user`.`id` IN <follower_ids>;
        friendships = Friendship.objects.filter(
            to_user=user,
        ).prefetch_related('from_user')
        # prefetch_related('from_user') 并不会立即查询数据库，而是
        # 1. 在 QuerySet 上标记：告诉 Django “当你真正访问 from_user 时，请批量取出相关对象”
        # 2. 延迟执行：数据库查询会在你访问数据时触发（比如迭代或 list(friendships)）
        # 3. 执行后: QuerySet 中每个 friendship.from_user 会被 指向缓存好的 User 实例，不会再发 SQL
        #    {from_user_id1: <User instance>,
        #     from_user_id2: <User instance>, ...}
        return [friendship.from_user for friendship in friendships]
        # 正确的写法三: 直接用 user_id instead of user

    @classmethod
    def has_followed(cls, from_user, to_user):
        # {request.user 眼中} zhuzhu的关注列表
        # 1. 小倔驴    [取关]
        # 2. 糖葫芦    [关注]
        # 3. 喵喵喵    [关注]
        return Friendship.objects.filter(
            from_user=from_user,
            to_user=to_user,
        ).exists()