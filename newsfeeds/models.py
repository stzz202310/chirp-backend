from django.contrib.auth.models import User
from django.db import models

from tweets.models import Tweet


class NewsFeed(models.Model):
    # 注意: user follow 了 tweet 的发帖人，所以 user's newsfeeds 有这个帖子
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # [冗余]等于tweet.created_at; 原因 必须是字段，才能 index_together

    class Meta:
        indexes = [
            models.Index(fields=('user', 'created_at'),),
        ]
        # index_together = (('user', 'created_at'),)
        constraints = [
            models.UniqueConstraint(fields=('user', 'tweet'), name='unique_user_tweet',),
        ]
        # unique_together = (('user', 'tweet'),)
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.created_at} inbox of {self.user}: {self.tweet}'
