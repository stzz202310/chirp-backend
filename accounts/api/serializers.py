from django.contrib.auth.models import User
from rest_framework import exceptions
from rest_framework import serializers

from accounts.models import UserProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username',)


class UserSerializerWithProfile(UserSerializer):
    # user.profile.nickname
    nickname = serializers.CharField(source='profile.nickname')
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'nickname', 'avatar_url',)

    def get_avatar_url(self, obj):
        # return obj.profile.avatar.url [如果 {obj.profile.avatar is None} 会报错]
        if obj.profile.avatar:
            return obj.profile.avatar.url
        return None


class UserSerializerForTweet(UserSerializerWithProfile):
    pass


class UserSerializerForComment(UserSerializerWithProfile):
    pass


class UserSerializerForLike(UserSerializerWithProfile):
    pass


class UserSerializerForFriendship(UserSerializerWithProfile):
    pass


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    # 用户输入的字段格式校验在 serializer 中处理
    # 但涉及到数据库查询 如 User.objects.filter(), 也可以放在 view 中处理
    def validate(self, data):
        data['username'] = data['username'].lower()
        if not User.objects.filter(username=data['username']).exists():
            raise exceptions.ValidationError({
                "username": "User does not exist.",
            })
        return data


class SignupSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=20, min_length=6)
    password = serializers.CharField(max_length=20, min_length=6)
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ('username', 'password', 'email',)

    def validate(self, data):
        # TODO [Homework] 增加验证 username 是不是只由给定的字符集合构成
        if User.objects.filter(username=data['username'].lower()).exists():
            raise exceptions.ValidationError({
                'username': 'This username has been occupied.',
            })

        if User.objects.filter(email=data['email'].lower()).exists():
            raise exceptions.ValidationError({
                'email': 'This email has been occupied.',
            })
        return data

    def create(self, validated_data):
        username = validated_data['username'].lower()
        email = validated_data['email'].lower()
        password = validated_data['password']

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        user.profile    # ⚠️ Create UserProfile object
        return user


class UserProfileSerializerForUpdate(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ('nickname', 'avatar',)    # 明确可更新字段白名单