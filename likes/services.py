from django.contrib.contenttypes.models import ContentType

from likes.models import Like


class LikesService(object):
    @classmethod
    def has_liked(cls, user, target):
        """""""""
        user: request.user 当前用户, 可能是匿名用户
        target: tweet OR comment

        has_likes 需要 user，target [仅 Like Model 的信息不够，所以不放在 models.py]
        TODO [HARD]: [comment x 10].has_liked
        Query 1. object_ids = [...]
        Query 2. Like.objects.filter(object_id__in=object_ids)
        """
        if user.is_anonymous:
            return False
        return Like.objects.filter(
            content_type=ContentType.objects.get_for_model(target.__class__),
            object_id=target.id,
            user=user,
        ).exists()