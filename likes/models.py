from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models.signals import pre_delete, post_save

from likes.listeners import incr_likes_count, decr_likes_count
from utils.memcached_helper import MemcachedHelper


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    object_id = models.PositiveIntegerField()
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True)
    content_object = GenericForeignKey(ct_field='content_type', fk_field='object_id')
    # content_object: 不会实际存储在数据库表中, 是 GenericForeignKey 提供的快捷访问属性
    # like.content_object: 返回具体关联的对象 (Tweet实例 或 Comment实例)

    class Meta:
        # 1. 保证同一个 user 不能对同一个对象重复点赞
        # 2. 查询某个 user 点赞过哪些 objects
        # unique_together = index_together + unique 约束
        unique_together = (('user', 'content_type', 'object_id'),)

        # 1. 查询某个 Tweet / Comment 的所有 likes,      并按照 created_at 时间排序
        # 2. 查询某个 user 给哪些 Tweet / Comment 点过赞, 并按照 created_at 时间排序
        index_together = (
            ('content_type', 'object_id', 'created_at'),
            ('user', 'content_type', 'created_at'),
        )

    def __str__(self):
        return '{} - {} liked {} {}'.format(
            self.created_at,
            self.user,
            self.content_type,
            self.object_id,
        )

    @property
    def cached_user(self):
        return MemcachedHelper.get_object_through_cache(
            model_class=User,
            object_id=self.user_id,
            # ⚠️ self.user.id 会触发 ORM 查询, 会额外访问数据库，失去缓存意义
        )

# ⚠️ 点赞后执行
# 1. 数据更新   Like 表单, incr_likes_count[Tweet 表单, Redis]
# 2. 发送通知   api.views.create() 中调用 send_like_notification
pre_delete.connect(receiver=decr_likes_count, sender=Like)
post_save.connect(receiver=incr_likes_count, sender=Like)