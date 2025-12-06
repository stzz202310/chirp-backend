from django.conf import settings
from django.core.cache import caches

from accounts.models import UserProfile
from twitter.cache import USER_PROFILE_PATTERN

cache = caches['testing'] if settings.TESTING else caches['default']


class UserService:

    @classmethod
    def get_profile_through_cache(cls, user_id):
        # user profile 比较特殊
        # 1. USER_PROFILE_PATTERN = 'userprofile:{user_id}'
        # 2. get_or_create
        key = USER_PROFILE_PATTERN.format(user_id=user_id)

        profile = cache.get(key)
        if profile is not None:
            return profile
        # 1. User.profile = property(get_profile)
        # 2. def get_profile(user):
        #       profile = UserService.get_profile_through_cache(user_id=user.id)
        # 根据 1 和 2，user 一定是存在的，不需要额外的检查
        profile, _ = UserProfile.objects.get_or_create(user_id=user_id)
        cache.set(key, profile)
        return profile

    @classmethod
    def invalidate_profile(cls, user_id):
        key = USER_PROFILE_PATTERN.format(user_id=user_id)
        cache.delete(key)