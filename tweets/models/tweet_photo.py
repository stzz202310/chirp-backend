from django.contrib.auth.models import User
from django.db import models

from tweets.constants import TweetPhotoStatus, TWEET_PHOTO_STATUS_CHOICES
from .tweet import Tweet


class TweetPhoto(models.Model):
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    file = models.FileField()
    order = models.IntegerField(default=0)
    status = models.IntegerField(
        default=TweetPhotoStatus.PENDING,
        choices=TWEET_PHOTO_STATUS_CHOICES,
    )
    # choices 接受一个可迭代序列, 每个元素为二元组: (实际存入数据库的值, 人类可读的显示名称)
    # 作用: 仅影响 admin 界面的显示, 对数据库字段本身无影响

    has_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (
            ('tweet', 'order'),
            ('user', 'created_at'),
            ('has_deleted', 'created_at'),
            ('status', 'created_at'),
        )

    def __str__(self):
        return f'{self.tweet_id}: {self.file}'