print(1)


"""
POST    /api/XXXs/      create      [write: request.data]
GET     /api/XXXs/      list        [read: request.query_params]
GET     /api/XXXs/1/    retrieve    [read: request.query_params]
DELETE  /api/XXXs/1/    destroy
PATCH   /api/XXXs/1/    partial_update
PUT     /api/XXXs/1/    update      [api.tests: comment.refresh_from_db()]


class CommentViewSet(viewsets.GenericViewSet):
    serializer_class = CommentSerializerForCreate
    queryset = Comment.objects.all()
    
    def get_permissions(self):  # 返回 list
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action in ['update', 'destroy',]:
            return [IsAuthenticated(), IsObjectOwner()] # obj = self.get_object()
        return [AllowAny()]
    
    (self, request, *args, **kwargs)
    def list():   serializer = Serializer(instance=self.get_queryset(), many=True)
                  return Response(data={'XXX': serializer.data}, status=status.HTTP_200_OK,)
    
    def create(): serializer = Serializer(data=data)    serializer.is_valid()   serializer.save()
                  return Response(data=Serializer(instance=instance).data, status=status.HTTP_201_CREATED,)
    
    def update(): instance = self.get_object()   serializer = Serializer(data=data, instance=instance)
                  serializer.is_valid()   serializer.save()
                  return Response(data=Serializer(instance=instance).data, status=status.HTTP_200_OK,)

    def destroy():instance = self.get_object()  instance.delete()
                  return Response(data={'success': True}, status=status.HTTP_200_OK,)
    
    
    自定义
    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    def followers(self, request, pk):
        detail=True 的 actions 会默认先去调用 get_object() {get_object_or_404()} 也就是
        queryset.filter(pk=1) 查询一下这个 object 在不在
    
    @action(methods=['GET'], detail=False)
    def login_status(self, request):

==============================================================================

/admin/

GET /api/users/                 ReadOnlyModelViewSet
GET /api/users/{pk=user_id}/    ReadOnlyModelViewSet

POST /api/accounts/signup/
POST /api/accounts/login/
POST /api/accounts/logout/
GET  /api/accounts/login_status/

POST    /api/comments/              create
PUT     /api/comments/1/            update
DELETE  /api/comments/1/            destroy
GET     /api/comments/?tweet_id=1   list, params=['tweet_id',]   {tweet_id=1}tweet 的所有 comments


POST /api/friendships/1/follow/     当前用户request.user 关注 follow   user_id=1 的用户
POST /api/friendships/1/unfollow/   当前用户request.user 取关 unfollow user_id=1 的用户
GET  /api/friendships/1/followers/  user_id=1 的用户 的粉丝列表
GET  /api/friendships/1/followings/ user_id=1 的用户 的关注列表

[Optional: list]
GET /api/friendships/?type=follower&to_user_id=1       查询某个用户的粉丝列表
GET /api/friendships/?type=following&from_user_id=1    查询某个用户的关注列表
GET /api/friendships/?from_user_id=1&to_user_id=2      查询两个人之间是否存在关注关系

[Optional: retrieve]
GET /api/friendships/1/?action=followers    查询某个用户的粉丝列表
GET /api/friendships/1/?action=followings   查询某个用户的关注列表


POST    /api/likes/         create, params=['content_type', 'object_id',] 点赞
POST    /api/likes/cancel/  cancel, params=['content_type', 'object_id',] 取消赞
DELETE  /api/likes/1/       destroy ❌ 依赖like.id: 前端 点赞 ==> 后端 返回like.id => 前端 才能取消赞

GET     /api/newsfeeds/     list    当前用户request.user 的新鲜事列表newsfeeds [tweet 合集]

GET  /api/tweets/?user_id=1     list, params=['user_id',]   {user_id=1}用户 的所有 tweets
GET  /api/tweets/1/             retrieve    {tweet_id=1}tweet [和它所有的 comments, likes]
POST /api/tweets/               create

"""