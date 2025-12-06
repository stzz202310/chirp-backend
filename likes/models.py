from django.contrib.auth.models import User
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from accounts.services import UserService


class Like(models.Model):
    # https://docs.djangoproject.com/en/3.1/ref/contrib/contenttypes/#generic-relations
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # {user} liked {content_object: content_type + object_id} at {created_at}
    object_id = models.PositiveIntegerField()   # comment id OR tweet id
    # user twitter; show tables; SELECT * FROM `django_content_type`;
    # id    app_label   model
    # 1     admin       logentry
    # 7     tweets      tweet
    # 8     friendships friendship ...
    content_type = models.ForeignKey(   # 选哪个表单(model): tweet OR comment
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
    )
    content_object = GenericForeignKey(ct_field='content_type', fk_field='object_id')
    # content_object: 并没有实际的保存在表单之中; 可以当作是一个快捷的访问方式
    # like.content_object: 具体的 tweet 或 comment

    class Meta:
        # 这里使用 unique together 会建一个 <user, content_type, object_id> 的索引
        # 这个索引同时还可以具备查询某个 user like 了哪些不同的 objects 的功能
        # 因此如果 unique together 改成 <content_type, object_id, user> 就没有这样的效果了
        unique_together = (('user', 'content_type', 'object_id'),)

        # 这个 index 的作用是可以按照时间顺序排序 {content_object: content_type + object_id} 的所有likes
        # 1. 某个 tweet | comment 所有 [按照时间排序] 的likes
        # 2. 某个 user 给哪些 tweet | comment [按照时间排序] 点过赞
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
        return UserService.get_user_through_cache(user_id=self.user_id)