from django.db import models
from django.contrib.auth.models import User
from utils.time_helpers import utc_now

class Tweet(models.Model):
    user = models.ForeignKey(   # user.tweet_set 等价于 Tweet.objects.filter(user=user)
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text='who posts this tweet',
    )   # 这篇帖子是谁发的
    content = models.CharField(max_length=255)  # 'abcde\0': \0表示字符串的结束
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        index_together = (('user', 'created_at'),)
        ordering = ('user', '-created_at',) # 不会对数据库产生影响，只会影响 QuerySet

    @property
    def hours_to_now(self): # tweet.hours_to_now
        # datetime.now 不带时区信息，需要加上 utc 的时区信息
        return (utc_now() - self.created_at).seconds // 3600

    def __str__(self):  # print(tweet instance)
        return f'{self.created_at} {self.user}: {self.content}'