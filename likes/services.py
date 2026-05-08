from django.contrib.contenttypes.models import ContentType

from likes.models import Like


class LikesService(object):
    @classmethod
    def has_liked(cls, user, target):
        # TODO [Myself] 优化 [comments x 10].has_liked
        if user.is_anonymous:
            return False
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(model=target.__class__),
            object_id=target.id,
            user=user,
        ).exists()