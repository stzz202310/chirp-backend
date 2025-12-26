from django.conf import settings

from django_hbase.client import HBaseClient
from .exceptions import BadRowKeyError, EmptyColumnError
from .fields import HBaseField, IntegerField, TimestampField


class HBaseModel:

    class Meta:
        table_name = None
        row_key = ()    # tuple, 顺序是固定的

    @classmethod
    def get_table(cls):
        conn = HBaseClient.get_connection()
        return conn.table(name=cls.get_table_name())

    @classmethod
    def get_field_hash(cls):
        field_hash = {}
        """
        obj.__dict__: 保存了 obj "实例级别"的属性及其值(⚠️不包含类属性), 本质上是一个 dict
        cls.__dict__: 当前类自己定义的所有属性 ✅方法本质上也是属性 ❌不包含父类, 不包含实例
        
        def get_field_hash(cls): 定义在 父类 HBaseModel, 所以
        ❌ 不在 HBaseFollowing.__dict__, 但可以调用 HBaseFollowing.get_field_hash()
        ✅ 在 HBaseModel.__dict__

                            是否查父类       是否能直接赋值
        cls.__dict__        ❌ 否           ❌ 否
        getattr(cls, 'x')   ✅ 是           ✅ 是   setattr(cls, 'new_attr', value)
        """
        for key in cls.__dict__:
            # field = cls.__dict__[key]
            field = getattr(cls, key)
            if isinstance(field, HBaseField):
                field_hash[key] = field
        return field_hash

    def __init__(self, **kwargs):
        # 调用构造函数 __init__
        # cls(**kwargs)|HBaseFollowing(**kwargs)|following = HBaseFollowing(from_user_id=1,...)
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
            #   column_key      => key
            #   'cf:to_user_id' => 'to_user_id'
            column_key = column_key.decode('utf-8')
            key = column_key[column_key.find(':') + 1:]
            data[key] = cls.deserialize_field(key=key, value=column_value)
        instance = cls(**data)
        return instance

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
    def serialize_row_key(cls, data, is_prefix=False):
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
                if is_prefix is False:
                    raise BadRowKeyError(f"{key} is missing in row key.")
                break
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
            # b = b'hello'
            # b.decode('utf-8') 等价于 str(b, encoding='utf-8'):  bytes => str
            # s = 'hello'
            # s.encode('utf-8') 等价于 bytes(s, encoding='utf-8'): str => bytes
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
            # column_key:   'cf:to_user_id'
            # column_value: '34'
            column_key = f'{field.column_family}:{key}'
            column_value = data.get(key)
            if column_value is None:
                continue
            row_data[column_key] = cls.serialize_field(field=field, value=column_value)
        return row_data

    @property
    def row_key(self):
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
        # instance = HBaseFollowing.get(from_user_id=123, created_at=timestamp)
        table = cls.get_table()
        row_key = cls.serialize_row_key(data=kwargs)
        row_data = table.row(row=row_key)
        instance = cls.init_from_row(row_key=row_key, row_data=row_data)
        return instance

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)    # 调用构造函数 __init__
        instance.save()
        return instance
    # TODO [Homework] 实现一个 get_or_create 的方法，返回 (instance, created)

    @classmethod
    def get_table_name(cls):
        if not cls.Meta.table_name:
            # NotImplementedError: 这个方法在当前类中没有实现，调用者应该在子类中实现它
            raise NotImplementedError("Missing table_name in HBaseModel meta class")
        if settings.TESTING:
            return f'test_{cls.Meta.table_name}'    # ⚠️
        return cls.Meta.table_name

    @classmethod
    def drop_table(cls):
        if not settings.TESTING:
            raise Exception('You can not drop table outside of unit tests')
        conn = HBaseClient.get_connection()
        conn.delete_table(name=cls.get_table_name(), disable=True)

    @classmethod
    def create_table(cls):
        if not settings.TESTING:
            raise Exception('You can not create table outside of unit tests')
        conn = HBaseClient.get_connection()
        tables = [table.decode('utf-8') for table in conn.tables()]
        if cls.get_table_name() in tables:
            return
        column_families = {
            # column_families =
            # { <key>          : <value> for ... }
            # { 'cf'           : {}      for ... }
            field.column_family: dict()
            for key, field in cls.get_field_hash().items()
            if field.column_family is not None
        }
        conn.create_table(
            name=cls.get_table_name(),
            families=column_families,   # {'cf': {}}
        )

    @classmethod
    def serialize_row_key_from_tuple(cls, row_key_tuple):
        if row_key_tuple is None:
            return None
        data = {
            key : value
            for key, value in zip(cls.Meta.row_key, row_key_tuple)
        }
        return cls.serialize_row_key(data=data, is_prefix=True)

    @classmethod
    def filter(cls, start=None, stop=None, prefix=None, limit=None, reverse=False):
        # start|stop|prefix=(from_user_id, created_at)
        # results = HBaseFollowing.filter(prefix=(1, None, None), limit=2, reverse=True)
        # results = HBaseFollowing.filter(start=(1, results[1].created_at, None), limit=2, reverse=True)

        # serialize tuple to str
        row_start = cls.serialize_row_key_from_tuple(row_key_tuple=start)
        row_stop = cls.serialize_row_key_from_tuple(row_key_tuple=stop)
        row_prefix = cls.serialize_row_key_from_tuple(row_key_tuple=prefix)

        # scan table
        table = cls.get_table()
        rows = table.scan(
            row_start=row_start,
            row_stop=row_stop,
            row_prefix=row_prefix,
            limit=limit,
            reverse=reverse,
        )

        # deserialize to instance list
        instances = []
        for row_key, row_data in rows:
            instance = cls.init_from_row(row_key=row_key, row_data=row_data)
            instances.append(instance)
        return instances


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

==================================================================================

1. instance = HBaseModel(from_user_id=1, ...); instance.save()
2. HBaseModel.create(from_user_id=1, to_user_id=2, created_at=ts)
3. instance.from_user_id = 2; instance.save()

following = HBaseFollowing(from_user_id=123, to_user_id=34, created_at=ts)
following.save()

key:    'from_user_id'
value:  123
field:  <django_hbase.models.fields.IntegerField object at 0xffffb2bc47c0>

str|bytes   table.put(row=self.row_key, data=row_data)
str|bytes   row_data = table.row(row=row_key)
⚠️ bytes    table.scan(row_start, row_stop, row_prefix)

conn.tables()                           # Return a list of table names available in this HBase instance
conn.table(name=cls.get_table_name())   # Return a table object
conn.delete_table(name=cls.get_table_name(), disable=True)
conn.create_table(name=cls.get_table_name(), families=column_families)


1. cls.__dict__ | HBaseFollowing.__dict__
{'__module__': 'friendships.hbase_models',
 'from_user_id': <django_hbase.models.fields.IntegerField object at 0xffffb2bc47c0>,
 'created_at': <django_hbase.models.fields.TimestampField object at 0xffffb2bc4880>,
 'to_user_id': <django_hbase.models.fields.IntegerField object at 0xffffb2bc48e0>,
 'Meta': <class 'friendships.hbase_models.HBaseFollowing.Meta'>, '__doc__': None}

2. field_hash = {key:field}: field 必须是 HBaseField 的实例
{'from_user_id': <django_hbase.models.fields.IntegerField object at 0xffffb2bc47c0>,
 'created_at': <django_hbase.models.fields.TimestampField object at 0xffffb2bc4880>,
 'to_user_id': <django_hbase.models.fields.IntegerField object at 0xffffb2bc48e0>,}

3. 构造函数 def __init__(self, **kwargs):
self.__dict__: {'from_user_id': 123, 'created_at': 1766539154271597, 'to_user_id': 34}

4. def save(self): 序列化
    data: {'from_user_id': 123, 'created_at': 1766539154271597, 'to_user_id': 34}
    row_data = self.serialize_row_data(data=self.__dict__)
    row_data: {'cf:to_user_id': '0000000000000034'}

    def row_key(self): return self.serialize_row_key(data=self.__dict__)
    row_key: b'3210000000000000:1766539154271597'
    
    table.put(row=self.row_key, data=row_data)
    {row_key                              : {column_key     : value}}
    {b'3210000000000000:1766539154271597' : {'cf:to_user_id': '0000000000000034'}}

5. def get(cls, **kwargs): 反序列化
    table: <happybase.table.Table name=b'test_twitter_followings'>
    row_key: b'3210000000000000:1766539154271597'
    row_data: {b'cf:to_user_id': b'0000000000000034'}
    row_data = table.row(row=row_key)

    def init_from_row(cls, row_key, row_data):
        data = cls.deserialize_row_key(row_key=row_key)
        data: {'from_user_id': 123, 'created_at': 1766539154271597}
        
        for column_key, column_value in row_data.items():
            data[key] = cls.deserialize_field(key=key, value=column_value)
        data: {'from_user_id': 123, 'created_at': 1766539154271597, 'to_user_id': 34}
        
        instance = HBaseFollowing(**data)
        instance = HBaseFollowing(from_user_id=123, to_user_id=34, created_at=ts)

"""