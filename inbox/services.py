from django.contrib.contenttypes.models import ContentType
from notifications.signals import notify

from comments.models import Comment
from tweets.models import Tweet


"""
方式 1 订阅模式 pre_delete, post_save
task 1 监听 signal A [signal A 代表 事件X]
task 2 监听 signal A
task 3 监听 signal A
事件 X 发生 => 发送 signal A => 触发 task 1, 2, 3 [用户注册 => 手机验证，发送欢迎邮件, ...]
1. task 1, 2, 3 之间不能有先后依赖关系
2. task 1, 2, 3 在不同地方，同时进行 [黑名单]

方式 2 [推荐，白名单 触发]
Service A:
    def signal_happened():
        task 1
        task 2
        task 3
"""
class NotificationService(object):

    @classmethod
    def send_like_notification(cls, like):
        target = like.content_object    # GenericForeignKey
        # 点赞用户 == 被点赞用户: 给自己的 Tweet | Comment 点赞
        if like.user == target.user:
            return
        if like.content_type == ContentType.objects.get_for_model(Tweet):
            notify.send(
                sender=like.user,
                recipient=target.user,
                verb='liked your tweet',
                target=target,
            )
        if like.content_type == ContentType.objects.get_for_model(Comment):
            notify.send(
                sender=like.user,
                recipient=target.user,
                verb='liked your comment',
                target=target,
            )

    @classmethod
    def send_comment_notification(cls, comment):
        target = comment.tweet
        if comment.user == target.user:
            return
        notify.send(
            sender=comment.user,
            recipient=target.user,
            verb='commented on your tweet',
            target=target,
        )