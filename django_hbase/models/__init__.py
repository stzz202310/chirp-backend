from .exceptions import *
from .fields import *
from .hbase_models import *

"""
1. models: exceptions, fields, hbase_models 
把一个"大文件"拆分成多个职责清晰的小文件，但对外暴露为一个统一的 models 模块

使用方式类似 Django ORM
from django_hbase.models import XXX
from django_hbase.models.__init__ import XXX
两者等价, 外部调用者不需要关心内部文件拆分情况

2. __init__.py 的作用
from .exceptions import *
from .fields import *
from .hbase_models import *
a. "." 表示当前目录, 从 __init__.py 同目录中导入 XXX.py
b. 将 exceptions | fields | hbase_models 中的内容统一提升到
   django_hbase.models 这一层, 对外形成一个干净、统一的 API

3. ⚠️相对路径导入
在 models 目录内部:
from .fields import XXX
from .exceptions import XXX
必须使用 相对路径，避免循环引用

❌ 绝对路径 循环引用
fields.py   from django_hbase.models.__init__ import XXXException
__init__.py from .fields import *

"""