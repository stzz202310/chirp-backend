print(1)


"""
/admin/

GET /api/users/
GET /api/users/{pk=user_id}

POST /api/accounts/signup/
POST /api/accounts/login/
POST /api/accounts/logout/
GET /api/accounts/login_status/

GET /api/tweets/?user_id=1
POST /api/tweets/

POST /api/friendship/1/follow/      当前用户关注 follow   user_id=1 的用户
POST /api/friendship/1/unfollow/    当前用户取关 unfollow user_id=1 的用户
GET /api/friendships/1/followers/   user_id=1 的用户 的粉丝列表
GET /api/friendships/1/followings/  user_id=1 的用户 的关注列表

[Optional]
GET /api/friendships/?type=follower&to_user_id=1       查询某个用户的粉丝列表
GET /api/friendships/?type=following&from_user_id=1    查询某个用户的关注列表
GET /api/friendships/?from_user_id=1&to_user_id=2      查询两个人之间是否存在关注关系

"""