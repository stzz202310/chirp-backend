from django.conf import settings

from django_hbase.client import HBaseClient
from .exceptions import BadRowKeyError, EmptyColumnError
from .fields import HBaseField, IntegerField, TimestampField


class HBaseModel:

    class Meta:
        table_name = None
        row_key = ()

    def __init__(self, **kwargs):
        for key, field in self.get_field_hash().items():
            value = kwargs.get(key)
            setattr(self, key, value)

    def save(self, batch=None):
        row_data = self.serialize_row_data(data=self.__dict__)
        if len(row_data) == 0:
            raise EmptyColumnError()
        if batch:
            batch.put(row=self.row_key, data=row_data)
        else:
            table = self.get_table()
            table.put(row=self.row_key, data=row_data)

    @classmethod
    def create(cls, batch=None, **kwargs):
        instance = cls(**kwargs)
        instance.save(batch=batch)
        return instance

    @classmethod
    def batch_create(cls, batch_data):
        table = cls.get_table()
        batch = table.batch()   # table 的信息已经在 batch 内部, batch 操作只会作用在这个 table 上
        instances = []
        for data in batch_data:
            instances.append(cls.create(batch=batch, **data))
        batch.send()
        return instances

    @classmethod
    def get(cls, **kwargs):
        table = cls.get_table()
        row_key = cls.serialize_row_key(data=kwargs)
        row_data = table.row(row=row_key)
        instance = cls.init_from_row(row_key=row_key, row_data=row_data)
        return instance

    @classmethod
    def delete(cls, **kwargs):
        row_key = cls.serialize_row_key(data=kwargs)
        table = cls.get_table()
        return table.delete(row=row_key)

    @property
    def row_key(self):
        return self.serialize_row_key(data=self.__dict__)

    @property
    def id(self):
        return self.row_key

    @classmethod
    def get_table(cls):
        conn = HBaseClient.get_connection()
        return conn.table(name=cls.get_table_name())

    @classmethod
    def get_table_name(cls):
        if not cls.Meta.table_name:
            raise NotImplementedError("Missing table_name in HBaseModel meta class")
        if settings.TESTING:
            return f'test_{cls.Meta.table_name}'
        return cls.Meta.table_name

    @classmethod
    def get_field_hash(cls):
        field_hash = {}
        for key in cls.__dict__:
            # field = cls.__dict__[key]
            field = getattr(cls, key)
            if isinstance(field, HBaseField):
                field_hash[key] = field
        return field_hash

    @classmethod
    def serialize_row_key(cls, data, is_prefix=False):
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
                raise BadRowKeyError(f"{key} should not contain ':' in value: {value}")
            values.append(value)
        return bytes(':'.join(values), encoding='utf-8')

    @classmethod
    def serialize_row_data(cls, data):
        row_data= {}
        field_hash = cls.get_field_hash()
        for key, field in field_hash.items():
            if not field.column_family:
                continue
            column_key = f'{field.column_family}:{key}'
            column_value = data.get(key)
            if column_value is None:
                continue
            row_data[column_key] = cls.serialize_field(field=field, value=column_value)
        return row_data

    @classmethod
    def serialize_field(cls, field, value):
        value = str(value)
        if isinstance(field, IntegerField):
            while len(value) < 16:
                value = '0' + value
        if field.reverse:
            value = value[::-1]
        return value

    @classmethod
    def init_from_row(cls, row_key, row_data):
        if not row_data:
            return None
        data = cls.deserialize_row_key(row_key=row_key)
        for column_key, column_value in row_data.items():
            # remove column family: 'cf:to_user_id'(column_key) => 'to_user_id'(key)
            column_key = column_key.decode('utf-8')
            key = column_key[column_key.find(':') + 1:]
            data[key] = cls.deserialize_field(key=key, value=column_value)
        instance = cls(**data)
        return instance

    @classmethod
    def deserialize_field(cls, key, value):
        field = cls.get_field_hash()[key]
        if field.reverse:
            value = value[::-1]
        if field.field_type in [IntegerField.field_type, TimestampField.field_type]:
            return int(value)
        return value

    @classmethod
    def deserialize_row_key(cls, row_key):
        data = {}
        if isinstance(row_key, bytes):
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
    def filter(cls, start=None, stop=None, prefix=None, limit=None, reverse=False):
        # start|stop|prefix = (from_user_id, created_at)
        # instances = HBaseFollowing.filter(prefix=(1,), limit=2, reverse=True)
        # instances = HBaseFollowing.filter(start=(1, results[1].created_at), limit=2, reverse=True)

        # 1. serialize tuple to str
        row_start = cls.serialize_row_key_from_tuple(row_key_tuple=start)
        row_stop = cls.serialize_row_key_from_tuple(row_key_tuple=stop)
        row_prefix = cls.serialize_row_key_from_tuple(row_key_tuple=prefix)

        # 2. scan table
        table = cls.get_table()
        rows = table.scan(
            row_start=row_start,
            row_stop=row_stop,
            row_prefix=row_prefix,
            limit=limit,
            reverse=reverse,
        )

        # 3. deserialize to instance list
        instances = []
        for row_key, row_data in rows:
            instance = cls.init_from_row(row_key=row_key, row_data=row_data)
            instances.append(instance)
        return instances

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
            # column_families[field.column_family] = dict()
            # column_families: {'cf': {}}
            field.column_family: dict()
            for key, field in cls.get_field_hash().items()
            if field.column_family is not None
        }
        conn.create_table(
            name=cls.get_table_name(),
            families=column_families,
        )