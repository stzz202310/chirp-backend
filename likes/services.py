from django.contrib.contenttypes.models import ContentType

from likes.models import Like


class LikesService(object):
    @classmethod
    def has_liked(cls, user, target):
        # user: request.user 当前用户, 可能是匿名用户
        # target: tweet OR comment
        if user.is_anonymous:
            return False
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(target.__class__),
            object_id=target.id,
            user=user,
        ).exists()