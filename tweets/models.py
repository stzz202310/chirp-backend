from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models

from likes.models import Like
from tweets.constants import TweetPhotoStatus, TWEET_PHOTO_STATUS_CHOICES
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
        index_together = (('user', 'created_at'),) # show index from `tweets_tweet`
        ordering = ('user', '-created_at',) # 不会对数据库产生影响，只会影响 QuerySet

    @property
    def hours_to_now(self): # tweet.hours_to_now
        # datetime.now 不带时区信息，需要加上 utc 的时区信息
        return (utc_now() - self.created_at).seconds // 3600

    # @property
    # def comments(self):
    #     return self.comment_set.all()
    #     return Comment.objects.filter(tweet=self)

    @property
    def like_set(self): # 并不是数据库表中的真实字段
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(Tweet),
            object_id=self.id,
        ).order_by('-created_at')

    def __str__(self):  # print(tweet instance)
        # 这里是你执行 print(tweet instance) 的时候会显示的内容
        return f'{self.created_at} {self.user}: {self.content}'


class TweetPhoto(models.Model):
    # 图片在哪个 Tweet 下面
    tweet = models.ForeignKey(Tweet, on_delete=models.SET_NULL, null=True)

    # 谁上传了这张图片，这个信息虽然可以从 tweet 中获取到，但是重复的记录在 TweetPhoto 里可以在
    # 使用上带来很多便利；比如某个人经常上传一些不合法的照片，那么这个人新上传的照片可以被标记
    # 为重点审核对象。或者我们需要封禁某个用户上传的所有图片的时候，就可以通过这个 model 快速进行筛选
    # tweet_photo.user = tweet_photo.tweet.user
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # 图片文件  tweetphoto.file[models.FileField()].url
    file = models.FileField()
    # 一个tweet下发了9张图片，可以通过 order 调整顺序
    order = models.IntegerField(default=0)

    # 图片状态，用于审核等情况 [IntegerField: 更灵活，可以随意更改对应的字符串]
    # lintcode 状态: AC, WA, TLE, CE, RTE
    status = models.IntegerField(
        default=TweetPhotoStatus.PENDING,
        choices=TWEET_PHOTO_STATUS_CHOICES,
    )

    # 软删除标记(soft delete, 类似回收站), 当一个照片被删除的时候，首先会被标记为已经被删除，在一定时间之后
    # 才会被真正的删除。这样做的目的是，如果在 tweet 被删除的时候马上执行真删除 通常会花费一定的
    # 时间，影响效率。可以用异步任务在后台慢慢做真删除
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