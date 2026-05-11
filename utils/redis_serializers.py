import json

from django.core import serializers

from django_hbase.models import HBaseModel
from utils.json_encoder import JSONEncoder


class DjangoModelSerializer:
    # DjangoModelSerializer(MySQL): 每次序列化 / 反序列化一个 instance
    # 序列化: instance → [instance] → serializers.serialize() → JSON 字符串
    # 反序列: JSON 字符串 → serializers.deserialize() → list(DeserializedObject)[0].object
    
    # print(instance.__dict__) 数据库的原始数据
    # {'_state': <django.db.models.base.ModelState object at 0xffffb1980160>,
    #  'id': 1,
    #  'user_id': 1,
    #  'content': 'hello zhuzhu',
    #  'created_at': datetime.datetime(2025, 12, 29, 5, 7, 48, 190038, tzinfo=<UTC>),
    #  'likes_count': 0,
    #  'comments_count': 0}

    # print(serialized_data)    JSON 字符串
    # [{"model": "tweets.tweet",
    #   "pk": 1,
    #   "fields": {"user": 1, "content": "hello zhuzhu", "created_at": "2025-12-29T05:11:16.530588Z",
    #              "likes_count": 0, "comments_count": 0}}]

    # [{"model": "newsfeeds.newsfeed",
    #   "pk": 1,
    #   "fields": {"user": 2, "tweet": 1, "created_at": "2026-05-08T17:10:11.263426Z"}}]

    @classmethod
    def serialize(cls, instance):
        # Django 的 serializers 默认需要一个 QuerySet 或者 list 类型的数据来进行序列化
        # 因此需要给 instance 加一个 [] 变成 list
        serialized_data = serializers.serialize(
            format='json',
            queryset=[instance],
            cls=JSONEncoder,
        )
        return serialized_data

    @classmethod
    def deserialize(cls, serialized_data):
        # deserialized_obj.object           ORM Model 实例  ✅
        # deserialized_obj.m2m_data         多对多关系数据
        # deserialized_obj.deferred_fields  延迟加载字段
        return list(serializers.deserialize(
            format='json',
            stream_or_string=serialized_data,
        ))[0].object    # [0] 对应 [instance]


class HBaseModelSerializer:
    # HBaseModelSerializer(HBase): 每次序列化 / 反序列化一个 instance
    # 序列化: instance → 遍历 field_hash 提取字段值 → json.dumps() → JSON 字符串
    # 反序列: JSON 字符串 → json.loads() → dict → 找到对应 HBaseModel 子类 → model_class(**json_data) 还原实例

    @classmethod
    def get_model_class(cls, model_class_name):
        for subclass in HBaseModel.__subclasses__():
            if subclass.__name__ == model_class_name:
                return subclass
        raise Exception(f'HBaseModel {model_class_name} not found.')

    @classmethod
    def serialize(cls, instance):
        # 额外存储 model_class_name, 用于反序列化时还原类型
        json_data = {'model_class_name': instance.__class__.__name__}
        for key in instance.get_field_hash():
            # {'from_user_id': <django_hbase.models.fields.IntegerField object at 0xffffb2bc47c0>,
            #  'created_at': <django_hbase.models.fields.TimestampField object at 0xffffb2bc4880>,
            #  'to_user_id': <django_hbase.models.fields.IntegerField object at 0xffffb2bc48e0>,}
            value = getattr(instance, key)
            json_data[key] = value
        return json.dumps(json_data)
        # json.dumps: dict (json_data) → str (serialized_data)
        # '{"model_class_name": "HBaseFollowing",
        #   "from_user_id": 1,
        #   "created_at": 1767770758299180,
        #   "to_user_id": 10}'

    @classmethod
    def deserialize(cls, serialized_data):
        json_data = json.loads(serialized_data) # str → dict
        model_class = cls.get_model_class(model_class_name=json_data['model_class_name'])
        del json_data['model_class_name']
        # HBaseFollowing(from_user_id=123, to_user_id=34, created_at=timestamp)
        return model_class(**json_data)