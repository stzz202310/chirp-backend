"""
循环引用

services:   from friendships.models import Friendship
models:     from friendships.listeners import invalidate_following_cache
listeners:  from friendships.services import FriendshipService
"""

def invalidate_following_cache(sender, instance, **kwargs):
    # instance: 被创建|删除的 instance
    # 如果可能被修改 def func(sender, instance, created, **kwargs):
    from friendships.services import FriendshipService
    FriendshipService.invalidate_following_cache(from_user_id=instance.from_user_id)