print(1)


"""
POST    /api/XXXs/      create
GET     /api/XXXs/      list        (read)
GET     /api/XXXs/1/    retrieve    (read)
DELETE  /api/XXXs/1/    destroy
PATCH   /api/XXXs/1/    partial_update
PUT     /api/XXXs/1/    update

def get_permissions(self):
    if self.action == 'create':
        return [IsAuthenticated()]
    return [AllowAny()]

==============================================================================

/admin/

GET /api/users/                 ReadOnlyModelViewSet
GET /api/users/{pk=user_id}     ReadOnlyModelViewSet

POST /api/accounts/signup/
POST /api/accounts/login/
POST /api/accounts/logout/
GET /api/accounts/login_status/

GET /api/tweets/?user_id=1      list
POST /api/tweets/               create

POST /api/friendships/1/follow/     当前用户关注 follow   user_id=1 的用户
POST /api/friendships/1/unfollow/   当前用户取关 unfollow user_id=1 的用户
GET /api/friendships/1/followers/   user_id=1 的用户 的粉丝列表
GET /api/friendships/1/followings/  user_id=1 的用户 的关注列表

[Optional: list]
GET /api/friendships/?type=follower&to_user_id=1       查询某个用户的粉丝列表
GET /api/friendships/?type=following&from_user_id=1    查询某个用户的关注列表
GET /api/friendships/?from_user_id=1&to_user_id=2      查询两个人之间是否存在关注关系

[Optional: retrieve]
GET /api/friendships/1/?action=followers    查询某个用户的粉丝列表
GET /api/friendships/1/?action=followings   查询某个用户的关注列表

POST /api/comments/     create


"""