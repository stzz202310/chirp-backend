from rest_framework.permissions import BasePermission


class IsObjectOwner(BasePermission):
    message = "You do not have permission to access this object."

    """
    DRF 会按顺序执行权限类:
    - 对于 detail=False 的 action，只调用 has_permission()
    - 对于 detail=True 的 action，会先调用 has_permission()，再调用 has_object_permission()
    
    如果权限检查未通过，默认返回的错误信息为 IsObjectOwner.message 中的内容
    """

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj): # obj = self.get_object()
        return request.user == obj.user


class IsCommentOwnerOrTweetOwner(BasePermission):
    message = "You do not have permission to delete this object."

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj):
        # request.user == obj.tweet.user: 多一次query
        return request.user == obj.user or request.user.id == obj.tweet.user_id