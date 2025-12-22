from django_hbase.client import HBaseClient
from .exceptions import BadRowKeyError, EmptyColumnError
from .fields import HBaseField, IntegerField, TimestampField


class HBaseModel:

    class Meta:
        table_name = None
        row_key = ()    # set

    @classmethod
    def get_table(cls):
        conn = HBaseClient.get_connection()
        if not cls.Meta.table_name:
            # NotImplementedError: 这个方法在当前类中没有实现，调用者应该在子类中实现它
            raise NotImplementedError("Missing table_name in HBaseModel meta class.")
        return conn.table(name=cls.Meta.table_name)

    @classmethod
    def get_field_hash(cls):
        # {field:field_obj} = {'from_user_id':models.IntegerField(reverse=True)}
        field_hash = {}
        for field in cls.__dict__:
            field_obj = getattr(cls, field)  # cls.__dict__[field]
            if isinstance(field_obj, HBaseField):
                field_hash[field] = field_obj
        return field_hash

    def __init__(self, **kwargs):
        for key, field in self.get_field_hash().items():
            value = kwargs.get(key)
            setattr(self, key, value)
            # 1. 加入 self.__dict__
            # 2. 加入 self.key, 比如 key 是 from_user_id, 可以通过 self.from_user_id 访问

    @classmethod
    def init_from_row(cls, row_key, row_data):
        if not row_data:
            return None
        data = cls.deserialize_row_key(row_key=row_key)
        for column_key, column_value in row_data.items():
            # remove column family
            column_key = column_key.decode('utf-8')
            key = column_key[column_key.find(':') + 1:]
            data[key] = cls.deserialize_field(key=key, value=column_value)
        return cls(**data)

    @classmethod
    def serialize_field(cls, field, value):
        value = str(value)
        if isinstance(field, IntegerField):
            # 因为排序规则是按照字典序排序，那么就可能出现 1 10 2 这样的排序
            # 解决的办法是固定 int 的位数为 16 位(8的倍数更容易利用空间), 不足位补 0
            while len(value) < 16:
                value = '0' + value
            # 时间戳 timestamp: int(time.time()*1000000) 正好 16 位，不需要补 0
        if field.reverse:
            value = value[::-1]
        return value

    @classmethod
    def deserialize_field(cls, key, value):
        field = cls.get_field_hash()[key]
        if field.reverse:
            value = value[::-1]
        if field.field_type in [IntegerField.field_type, TimestampField.field_type]:
            return int(value)
        return value

    @classmethod
    def serialize_row_key(cls, data):
        """""""""
        serialize dict to bytes (not str)
        {key1: val1}                         => b"val1"
        {key1: val1, key2: val2}             => b"val1:val2"
        {key1: val1, key2: val2, key3: val3} => b"val1:val2:val3"
        
        需要[根据查询需求]定义 row_key 的顺序:
        row_key = (key1, key2) = ('from_user_id', 'created_at')
        """
        field_hash = cls.get_field_hash()
        values = []
        # 写法 1: 如果 field 没有定义 column_family, 那这个 field 就是 row_key
        # for key, field in field_hash.items():
        #     if field.column_family:
        #         continue

        # 写法 2: 根据 Meta.row_key 中定义的 row_key 的顺序
        for key in cls.Meta.row_key:
            field = field_hash.get(key)
            value = data.get(key)
            if value is None:
                raise BadRowKeyError(f"{key} is missing in row key.")
            value = cls.serialize_field(field=field, value=value)
            if ':' in value:
                # val 不能有冒号":", 否则解析时会报错
                raise BadRowKeyError(f"{key} should not contain ':' in value: {value}")
            values.append(value)
        return bytes(':'.join(values), encoding='utf-8')

    @classmethod
    def deserialize_row_key(cls, row_key):
        """""""""
        "val1" =>           {'key1': val1, 'key2': None, 'key3': None}
        "val1:val2" =>      {'key1': val1, 'key2': val2, 'key3': None}
        "val1:val2:val3" => {'key1': val1, 'key2': val2, 'key3': val3}
        """
        data = {}
        if isinstance(row_key, bytes):
            # bytes -> str
            row_key = row_key.decode('utf-8')

        # [val1:val2 => val1:val2:] 方便每次 find(':') 都能找到一个 val
        row_key = row_key + ':'
        for key in cls.Meta.row_key:
            index = row_key.find(':')
            if index == -1:
                break
            data[key] = cls.deserialize_field(key=key, value=row_key[:index])
            row_key = row_key[index + 1:]
        return data

    @classmethod
    def serialize_row_data(cls, data):
        row_data= {}
        field_hash = cls.get_field_hash()
        for key, field in field_hash.items():
            if not field.column_family:
                continue
            # key: 'from_user_id'
            column_key = f'{field.column_family}:{key}'
            column_value = data.get(key)
            if column_value is None:
                continue
            row_data[column_key] = cls.serialize_field(field=field, value=column_value)
        return row_data

    @property
    def row_key(self):
        # obj.__dict__: 保存了 obj "实例级别"的属性及其值(⚠️不包含类属性), 本质上是一个 dict
        return self.serialize_row_key(data=self.__dict__)

    def save(self):
        row_data = self.serialize_row_data(data=self.__dict__)
        # 如果 row_data={column key:value} 为空, hbase 会直接不存储这个 row_key
        # 因此我们可以 raise 一个 exception 提醒调用者, 避免储存空值
        if len(row_data) == 0:
            raise EmptyColumnError()
        table = self.get_table()
        table.put(row=self.row_key, data=row_data)

    @classmethod
    def get(cls, **kwargs):
        # HBaseModel.get(from_user_id=1, created_at=ts)
        row_key = cls.serialize_row_key(data=kwargs)
        table = cls.get_table()
        row = table.row(row=row_key)
        # return obj: obj.from_user_id, obj.to_user_id
        return cls.init_from_row(row_key=row_key, row_data=row)

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        # instance = HBaseModel(**kwargs)
        # 传给了构造函数 __init__
        instance.save()

        # 1. HBaseModel.create(from_user_id=1, to_user_id=2, created_at=ts)
        # 2. instance = HBaseModel(from_user_id=1, ...); instance.save()
        # 3. instance.from_user_id = 2; instance.save()
        return instance

"""
MySQL vs HBase 设计对比: friendships_friendship Table

1. MySQL
Friendship: id, from_user_id, to_user_id, created_at
index_together: 
    ('from_user', 'created_at'),
    ('to_user', 'created_at'),
    每个联合索引在底层都相当于一棵独立的 B+Tree [可以理解为"额外的一张索引表"]

1 张数据表 + 2 个联合索引 ≈ 3 份有序数据结构

2. HBase
  a. HBase 没有二级索引, 每一个"index_together"都需要 单独一张表
  b. RowKey 通常由多个字段组合，用来支持等值 + 范围查询 [RK = 查询条件的组合]

RK1 = from_user_id
RK2 = from_user_id + created_at
RK1: 只能查 from_user_id = XX, 不支持 created_at 做范围查询
RK2: 支持的查询等同于 index_together ('from_user', 'created_at')
"""