from rest_framework.permissions import BasePermission


class IsObjectOwner(BasePermission):
    """
    这个 Permission 负责检查 obj.user == request.user
    这个类是比较通用的，今后如果有其他用到这个类的地方，可以将文件放到一个共享的位置

    Permission 会一个个被执行
    - 如果是 detail=False 的 action，只检查 has_permission
    - 如果是 detail=True 的 action，同时检查 has_permission 和 has_object_permission

    如果没有权限，默认的错误信息会显示 IsObjectOwner.message 中的内容
    """
    message = "You do not have permission to access this object."

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj): # obj = self.get_object()
        return request.user == obj.user


class IsCommentOwnerOrTweetOwner(BasePermission):
    message = "You do not have permission to delete this object."

    def has_permission(self, request, view):
        return True

    def has_object_permission(self, request, view, obj): # obj = self.get_object()
        # request.user == obj.tweet.user: 多一次query
        return request.user == obj.user or request.user.id == obj.tweet.user_id