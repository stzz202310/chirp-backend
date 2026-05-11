from django_hbase import models


class HBaseFollowing(models.HBaseModel):    # from_user_id 的关注列表
    from_user_id = models.IntegerField(reverse=True)
    created_at = models.TimestampField()
    # 时间戳 timestamp: int(time.time()*1000000), 例 1766368427850129
    # DateTimeField: '2025-12-21 10:00:00.000000'
    to_user_id = models.IntegerField(column_family='cf')

    class Meta:
        # row_key = reverse(from_user_id) + created_at, 可以支持查询
        # - A 关注的所有人按照关注时间排序
        # - A 在某个时间段内关注的人有哪些
        # - A 在某个时间点之后/之前关注的前 X 个人是谁
        row_key = ('from_user_id', 'created_at')
        table_name = 'twitter_followings'

    def save(self, batch=None):
        from friendships.services import FriendshipService
        FriendshipService.invalidate_following_cache(from_user_id=self.from_user_id)
        super(HBaseFollowing, self).save(batch=batch)

    @classmethod
    def delete(cls, **kwargs):
        from friendships.services import FriendshipService
        from_user_id = kwargs.get('from_user_id')
        if from_user_id is not None:
            FriendshipService.invalidate_following_cache(from_user_id=from_user_id)
        return super(HBaseFollowing, cls).delete(**kwargs)


class HBaseFollower(models.HBaseModel):     # to_user_id 的粉丝列表
    to_user_id = models.IntegerField(reverse=True)
    created_at = models.TimestampField()
    from_user_id = models.IntegerField(column_family='cf')

    class Meta:
        # row_key = reverse(to_user_id) + created_at, 可以支持查询:
        # - A 的所有粉丝按照关注时间排序
        # - A 在某个时间段内被哪些粉丝关注了
        # - 在某个时间点之后/之前关注了 A 的前 X 个人是谁
        row_key = ('to_user_id', 'created_at')
        table_name = 'twitter_followers'