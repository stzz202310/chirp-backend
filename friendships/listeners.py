"""""""""
循环引用

services:   from friendships.models import Friendship
models:     from friendships.listeners import invalidate_following_cache
listeners:  from friendships.services import FriendshipService
"""

def invalidate_following_cache(sender, instance, **kwargs):
    # def func(sender, instance, [created], **kwargs):
    # instance: 被创建|修改|删除的 instance
    from friendships.services import FriendshipService
    FriendshipService.invalidate_following_cache(from_user_id=instance.from_user_id)