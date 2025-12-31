from django_hbase import models


class HBaseFollowing(models.HBaseModel):
    # row key
    from_user_id = models.IntegerField(reverse=True)
    created_at = models.TimestampField()
    # 时间戳 timestamp: int(time.time()*1000000), 例 1766368427850129
    # DateTimeField: '2025-12-21 10:00:00.000000'

    # column key
    to_user_id = models.IntegerField(column_family='cf')

    """
    存储 from_user_id follow 了哪些人 [from_user_id 的关注列表]
    row_key 按照 from_user_id + created_at 排序, 可以支持查询:
     - A 关注的所有人按照关注时间排序
     - A 在某个时间段内关注的人有哪些
     - A 在某个时间点之后/之前关注的前 X 个人是谁
    """

    class Meta:
        row_key = ('from_user_id', 'created_at')
        table_name = 'twitter_followings'

    def save(self):
        # HBase Model: 不走 Django ORM [pre_delete / post_save 不会自动触发]
        # 正确做法：在「写 / 删 HBase」的地方主动失效缓存
        # TODO [Myself] 若未来支持批量写/删(多RowKey), 这里需要失效多条缓存
        from friendships.services import FriendshipService
        FriendshipService.invalidate_following_cache(from_user_id=self.from_user_id)
        super(HBaseFollowing, self).save()

    @classmethod
    def delete(cls, **kwargs):
        from friendships.services import FriendshipService
        from_user_id = kwargs.get('from_user_id')
        if from_user_id is not None:
            FriendshipService.invalidate_following_cache(from_user_id=from_user_id)
        # ⚠️ 一定要把 kwargs 继续传下去
        return super(HBaseFollowing, cls).delete(**kwargs)


class HBaseFollower(models.HBaseModel):
    # row key
    to_user_id = models.IntegerField(reverse=True)
    created_at = models.TimestampField()

    # column key
    from_user_id = models.IntegerField(column_family='cf')

    """""""""
    存储 to_user_id 被哪些人 follow 了 [to_user_id 的粉丝列表]
    row_key 按照 to_user_id + created_at 排序, 可以支持查询:
     - A 的所有粉丝按照关注时间排序
     - A 在某个时间段内被哪些粉丝关注了
     - 哪 X 人在某个时间点之后/之前关注了 A
    """

    class Meta:
        row_key = ('to_user_id', 'created_at')
        table_name = 'twitter_followers'