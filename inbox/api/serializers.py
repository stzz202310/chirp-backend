from rest_framework import serializers
from notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = (
            'id',
            'actor_content_type',
            'actor_object_id',
            'verb',
            'action_object_content_type',
            'action_object_object_id',
            'target_content_type',
            'target_object_id',
            'timestamp',
            'unread',
        )
        """
        recipient = request.user
        actor：发起动作的人/对象
        verb：动作本身（如 “liked”, “commented”, “followed”）
        action_object（可选）：动作的核心对象（如点赞的是一条评论）
        target（可选）：动作发生的场景或最终目标（如评论属于哪篇文章）
        
        verb = '给你的帖子{target}点了赞'
        verb = 'liked your tweet {target}'
        
        ✅ 例子 1：小明 点赞 了 小红的文章
        actor：小明（User 对象）
        verb：liked
        action_object：无（也可以是 "Like" 实体）
        target：小红的文章（Article 对象）
        句子就是：
        小明 (actor) liked (verb) 小红的文章 (target)
        
        ✅ 例子 2：小明 评论 了 小红的文章
        actor：小明（User）
        verb：commented
        action_object：那条评论（Comment 对象）
        target：文章（Article）
        构成句子：
        小明 (actor) commented (verb) a comment (action_object) on 小红的文章 (target)

        ✅ 例子 3：小明 关注 了 小红
        actor：小明
        verb：followed
        action_object：无
        target：小红（User）
        句子：
        小明 (actor) followed (verb) 小红 (target)
        
        ✅ 例子 4：系统 推送 了 一条公告
        actor：系统（SystemUser 或 None）
        verb：published
        action_object：公告（Announcement）
        target：无或全部用户（看你实现）
        """