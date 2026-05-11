"""""""""

============================================================
1. models.py
============================================================
@property
def cached_user(self):  # 返回 obj 或 QuerySet

def __str__(self):      # 执行 print(tweet_instance) 时会显示的内容


============================================================
2. api.views
============================================================
def get_permissions(self):  # ⚠️ 返回 list
                            # return [AllowAny()]
                            # return [IsAuthenticated(), IsObjectOwner()]

def get_queryset(self):     # 定义当前 ViewSet 的数据范围
def get_object(self):       # 在数据范围内获取单个对象
    queryset = self.filter_queryset(self.get_queryset()) ...
    obj = get_object_or_404(queryset, **filter_kwargs)   ...
    return obj

----------------------------------------------

def list(self, request, *args, **kwargs):
def retrieve(self, request, *args, **kwargs):
def create(self, request, *args, **kwargs):
def update(self, request, *args, **kwargs):
def destroy(self, request, *args, **kwargs):

def list():     # class ListModelMixin: 参考
                #   queryset = self.filter_queryset(self.get_queryset())
                #   page = self.paginate_queryset(queryset) ...
                serializer = Serializer(instance=queryset, many=True)
                return Response(data={'XXX': serializer.data}, status=status.HTTP_200_OK,)
              
def retrieve(): ⚠️ pk = kwargs.get('pk')
                instance = self.get_object()
                serializer = Serializer(instance=instance)
                return Response(data=serializer.data, status=status.HTTP_200_OK,)

def create():   serializer = Serializer(data=request.data)
                serializer.is_valid()
                instance = serializer.save()
                return Response(data=Serializer(instance=instance).data, status=status.HTTP_201_CREATED,)

def update():   instance = self.get_object()
                serializer = Serializer(instance=instance, data=request.data)
                serializer.is_valid()
                instance = serializer.save()
                return Response(data=Serializer(instance=instance).data, status=status.HTTP_200_OK,)

def destroy():  instance = self.get_object()
                instance.delete()
                # DRF 默认 destroy 返回 status=status.HTTP_204_NO_CONTENT
                # 这里改为返回 {"success": True}, 让前端更直观地判断操作是否成功, 因此返回 HTTP 200 更合适
                return Response(data={'success': True}, status=status.HTTP_200_OK,)

----------------------------------------------

@action(methods=['GET'], detail=False, url_path='unread-count')
def unread_count(self, request, *args, **kwargs):
    ❌ queryset = self.filter_queryset(queryset=self.get_queryset()) ...

@action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
def follow(self, request, pk):
    ⚠️ pk = int(pk)
    instance = self.get_object() ...


============================================================
3. api.serializers
============================================================
class Serializer(serializers.ModelSerializer):
    user = UserSerializerForComment()
    user = UserSerializerForFriendship(source='from_user')          # instance = friendship.from_user
    comments = CommentSerializer(source='comment_set', many=True)   # queryset = tweet.comment_set
    
    tweet = serializers.SerializerMethodField()
    def get_tweet(self, obj):
        # self: 当前 Serializer 实例
        # obj:  当前正在被序列化的 Model 实例
        ...
        return TweetSerializer(instance=obj.cached_tweet, context=self.context).data
        return TweetSerializer(...) 返回 Serializer 对象而非数据 ❌
        
        1) .data
        ModelSerializer 字段 (DRF 自动处理, 无需手动调用): tweet = TweetSerializer(...)
        SerializerMethodField (自己控制序列化, 必须手动调用): return TweetSerializer(...).data
        
        2) context
        ModelSerializer 字段: DRF 自动将 context 传入嵌套 Serializer
        SerializerMethodField: 无自动传递，必须手动透传，否则嵌套 Serializer 拿不到 


    def __init__(self, instance=None, data=empty, **kwargs):
    
    class Meta:
        model = User
        fields = ('id', 'username',)

    --------------------------------------------------------------------------------------
    
    # request.data:   原始客户端输入数据，未校验
    # attrs:          validate() 的参数, 字段级验证后的原始输入数据
    # validated_data: validate() 返回值, 字段级验证 + validate() 处理后的数据
                      通过全部校验后生成, 安全 可直接用于 create()/update()
    
    def validate(self, attrs):                  return attrs    # = return serializer.validated_data
    def create(self, validated_data):           return instance
    def update(self, instance, validated_data): return instance [修改后的 instance]
    def save(self, **kwargs):                   return self.instance
    
    def cancel(self):
    
    --------------------------------------------------------------------------------------
    
    ModelSerializer 默认实现了 save(), create() 和 update() 方法，大致逻辑是:
    
    def create(self, validated_data):
        # NOT def create(self):
        # - 保持 create() 接口独立、可测试
        # - 不依赖 Serializer 的内部状态 (如 self.validated_data)
        ModelClass = self.Meta.model
        instance = ModelClass.objects.create(**validated_data)
        return instance
    
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
    
    def save(self, **kwargs):        
        if self.instance is not None: self.instance = self.update(self.instance, validated_data)
        else: self.instance = self.create(validated_data)
        return self.instance


============================================================
4. 序列化 / 反序列化流程
============================================================
✅ 调用在 views
✅ 数据处理逻辑在 serializers

1️⃣ 序列化 (Object -> JSON / dict)
   serializer = TweetSerializer(instance=tweet)
   serializer.data  # 得到序列化后的字典
    
   1) instance 可以是 单个模型对象 或 QuerySet/列表 (many=True)
   2) 返回给前端通常是 dict 包裹 list，而不是裸 list
      comments = Comment.objects.filter(tweet_id=1)
      serializer = CommentSerializer(instance=comments, many=True)
      print(serializer.data)
      [{"id": 1, "content": "Nice tweet!", "user": 2},
       {"id": 2, "content": "I agree!", "user": 3},]
       
      return Response(data={'comments': serializer.data})
      {"comments": [
          {"id": 1, "content": "Nice tweet!", "user": 2},
          {"id": 2, "content": "I agree!", "user": 3},]}
    
    3) serializers.SerializerMethodField()
       ✅ SerializerMethodField 只用于序列化 (read-only)
       ❌ 不参与反序列化 (write / 校验 / 保存)


2️⃣ 反序列化 (客户端数据 -> Python 对象)
   serializer = TweetSerializer(data=request.data)
   serializer.is_valid()       # 执行 字段级验证 + validate()
   serializer.errors           # You must call .is_valid() before accessing .errors
   serializer.validated_data   # 校验后的安全数据
   serializer.save()           # 调用 create() 或 update(), return instance


============================================================
5. Serializer 中如何使用 request.user
============================================================

方法 1: user 通过 context 传入, 不暴露给客户端 [更推荐]
# tweets.api.views
def create(self, request):
    serializer = TweetSerializerForCreate(data=request.data, context={'request': request},)

# tweets.api.serializers
class TweetSerializerForCreate(serializers.ModelSerializer):
    class Meta:
        model = Tweet
        fields = ('content', 'files')           # user 不在白名单, 客户端无法传入或篡改
            
    def create(self, validated_data):
        user = self.context['request'].user     # 从 context 取, 服务端强制指定，安全


方法 2: user_id 由 View 组装后传入 data, 需在 fields 里声明
# tweets.api.views
def create(self, request):
    data = {
        'user_id': request.user.id,             # View 层强制覆盖, 客户端传入的 user_id 被忽略
        'content': request.data.get('content'),
    }
    serializer = TweetSerializerForCreate(data=data)

# tweets.api.serializers
class TweetSerializerForCreate(serializers.ModelSerializer):
    user_id = serializers.IntegerField()        # 需显式声明，否则 Serializer 不认识该字段
    class Meta:
        model = Tweet
        fields = ('user_id', 'content', 'files')
    
    # user_id 已在 validated_data 中, ModelSerializer 默认 create() 可直接处理，无需重载

"""