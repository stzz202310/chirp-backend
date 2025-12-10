from django.core import serializers

from utils.json_encoder import JSONEncoder


class DjangoModelSerializer:
    # 序列化:   obj ==> 字符串 [tweet ==> 字符串，保存在 redis 中]
    # 反序列化: 字符串 ==> obj

    @classmethod
    def serialize(cls, instance):
        # Django 的 serializers 默认需要一个 QuerySet 或者 list 类型的数据来进行序列化
        # 因此需要给 instance 加一个 [] 变成 list
        return serializers.serialize(
            format='json',
            queryset=[instance],
            cls=JSONEncoder,
        )

    @classmethod
    def deserialize(cls, serialized_data):
        # 需要加 .object 来得到原始 model 类型的 object 数据，要不然得到的数据并不是一个
        # ORM 的 object，而是一个 DeserializedObject 的类型
        return list(serializers.deserialize(
            format='json',
            stream_or_string=serialized_data,
        ))[0].object    # [0] 对应 [instance]