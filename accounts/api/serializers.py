from django.contrib.auth.models import User
from rest_framework import exceptions
from rest_framework import serializers


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email',)


class UserSerializerForTweet(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username',)


class UserSerializerForComment(UserSerializerForTweet):
    pass


class UserSerializerForLike(UserSerializerForTweet):
    pass


class UserSerializerForFriendship(UserSerializerForTweet):
    pass


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

    # 用户输入的字段格式校验在 serializer 中处理
    # 但涉及到数据库查询（如 User.objects.filter(), 也可以放在 view 中处理
    def validate(self, data):
        data['username'] = data['username'].lower()
        if not User.objects.filter(username=data.get('username')).exists():
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

        """
        serializer.is_valid() DRF 会依次执行 三个步骤:
        步骤 1：字段级验证 (Field-level validation)     username = serializers.CharField(min_length=6, max_length=20)
        步骤 2：自定义字段级验证方法 (Optional)  serializers.py: def validate_<fieldname>(self, data):
        步骤 3：全局验证 validate(self, data)  serializers.py: def validate(self, data): 会覆盖父类的全局 validate 方法
        """
    def validate(self, data):
        if User.objects.filter(username=data.get('username').lower()).exists():
            raise exceptions.ValidationError({
                'username': 'This username has been occupied.',
            })

        if User.objects.filter(email=data.get('email').lower()).exists():
            raise exceptions.ValidationError({
                'email': 'This email has been occupied.',
            })
        return data

    def create(self, validated_data):
        username = validated_data.get('username').lower()
        email = validated_data.get('email').lower()
        password = validated_data.get('password')

        # .create() 明文保存密码 password = "123456"
        # - 登录验证无法通过（Django 认证系统只认加密密码）
        # - 极大的安全问题（数据泄漏 = 密码直接暴露）

        # .create_user() 密码存入数据库时是哈希加密的 user.set_password(password)
        # password = "pbkdf2_sha256$390000$Uq4Wj7..."
        # username 和 email 需要进行一些 normalize 规范化处理
        # 创建用户时必须使用 create_user() {user.set_password()}
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        return user



