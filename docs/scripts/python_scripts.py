
# ============================================================
# 1. isinstance(obj, Class)
# ============================================================
# isinstance(obj, Class): 判断 obj 是否是 Class 的实例 (包含子类实例, 推荐用法)
# type(obj) == Class: 判断 obj 是否 严格是 Class 的实例 (不包含子类)
# type(obj) 等价于 obj.__class__ [注意: __class__ 是属性，不是函数]

class A: pass
class B(A): pass

a = A()
b = B()

isinstance(a, A)    # True
isinstance(a, B)    # False
isinstance(b, A)    # True  ✅ 子类实例
isinstance(b, B)    # True

# 支持 元组 (一次判断多个类型)
# isinstance(obj, (A, B, C))    等价于
# isinstance(obj, A) or isinstance(obj, B) or isinstance(obj, C)
isinstance(a, (A, B))   # True
isinstance(b, (A, B))   # True

# type(a) 或 a.__class__     # <class '__main__.A'>
print(type(a) == A)     # True
print(type(a) == B)     # False
print(a.__class__ == B) # False

# Class.__subclasses__(): 查看某个类的"直接子类", 只返回"直接子类", 不会递归返回所有后代类
class C(B): pass     # C 不是 A 的直接子类

A.__subclasses__()   # [<class '__main__.B'>]
B.__subclasses__()   # [<class '__main__.C'>]


# ============================================================
# 2. * / ** 解包（unpacking）
# ============================================================
# * 用于展开 iterable（如 list / tuple）
# ** 用于展开 dict（key-value）

# 2.1 * 展开 list / tuple
a = [1, 2]
b = [3, 4]

c1 = [a, b]         # [[1, 2], [3, 4]]
c2 = [*a, *b]       # [1, 2, 3, 4]     ← 展开
c3 = {*a, *b}       # {1, 2, 3, 4}     ← set 去重

# 2.2 ** 展开 dict
a = {'x': 1}
b = {'y': 2}

d1 = [a, b]         # [{'x': 1}, {'y': 2}]
d2 = {*a, *b}       # {'x', 'y'}  ← 展开的是 key，不是 dict
d3 = {**a, **b}     # {'x': 1, 'y': 2}

# 2.3 函数调用中的 **kwargs 解包
def func(x, y):
    return x + y

kwargs = {'x': 1, 'y': 2}
func(**kwargs)      # 等价于 func(x=1, y=2)
# **kwargs：将一个 dict 解包为关键字参数, ⚠️dict 的 key 必须与函数参数名一致


# ============================================================
# 3. hasattr / getattr / setattr (动态属性访问)
# ============================================================
# 用于在运行时读取 / 设置对象属性
# hasattr(obj, key)
# getattr(obj, key, default=None)
# setattr(obj, key, value)
# ⚠️ key 必须是字符串 (str)
# ⚠️ value 几乎没有类型限制 (int, str, list, dict, None, 自定义对象 object)

# dir(obj) 返回对象可访问的所有属性和方法名列表 (包括实例属性、类属性、方法、property、内置属性)
# obj.__dict__ 返回对象实例的属性字典 "这个对象自己有啥" ✅只包含"实例自身"的属性 ❌不包含类属性 方法 property 等
# cls.__dict__ 返回当前类定义的属性字典 "这个类定义了啥" ✅包含类中定义的变量,方法 ❌不包含父类中的属性, 不包含实例属性

class Parent:
    parent_attr = "I'm parent"
    def parent_method(self):
        return "parent's method called"

class MyClass(Parent):
    class_attr = "I'm class attr"
    def __init__(self, x):
        self.x = x  # 实例属性
    def method(self):
        return "method called"

obj = MyClass(10)
hasattr(obj, 'name')            # False
setattr(obj, 'name', 'Alice')   # 动态添加属性
getattr(obj, 'name')            # 'Alice'   obj.name
hasattr(obj, 'name')            # True
getattr(obj, 'age', None)       # None（属性不存在时返回默认值）
# setattr(user, 123, 'x')       # ❌ TypeError

obj.__dict__        # {'x': 10, 'name': 'Alice'};
                    # ✅只包含实例属性 x
                    # ❌不包含 class_attr, method, parent_attr, parent_method

MyClass.__dict__    # {'__module__': '__main__',
                    # 'class_attr': "I'm class attr",
                    #  '__init__': <function MyClass.__init__ at 0x105021f70>,
                    #  'method': <function MyClass.method at 0x105033040>, '__doc__': None}}
                    # ✅包含类自己定义的属性和方法
                    # ❌不包含实例属性 x, 不包含父类 Parent 的 parent_attr, parent_method

dir(obj)            # ['__class__', ..., 'class_attr', 'method', 'name', 'parent_attr', 'parent_method', 'x']
obj.method()        # 'method called'
obj.parent_method   # "parent's method called"
obj.class_attr      # "I'm class attr"
obj.parent_attr     # "I'm parent"

# 1) obj.__dict__ 不包含 class_attr, method, parent_attr, parent_method, 但 obj.XXX 是可以访问到的
#    因为 Python 会按顺序查找: 实例自身(obj.__dict__) -> 类(MyClass.__dict__) -> 父类 (Parent.__dict__)
# 2) dir(obj) 中存在的属性，通常都可以通过 obj.XXX 或 getattr(obj, 'XXX') 访问 [⚠️ 注意引号]


# ============================================================
# 4. encode / decode
# ============================================================
# Python 中字符串与字节的转换
# - str.encode(encoding='utf-8')    str → encode → bytes
# - bytes.decode(encoding='utf-8')  bytes → decode → str

# 示例 1：str → bytes
s = "hello"
b = s.encode(encoding='utf-8')      # b = b'hello'
# b = str.encode(s, encoding='utf-8') 这两种写法 完全等价
print(b, type(b))                   # b'hello' <class 'bytes'>

# 示例 2：bytes → str
b2 = b'world'
s2 = b2.decode(encoding='utf-8')    # s2 = 'world'
print(s2, type(s2))                 # world <class 'str'>

# 注意事项: 编码和解码必须使用相同的 encoding, 否则可能报 UnicodeDecodeError / UnicodeEncodeError
# 常用 encoding：'utf-8'(推荐，支持中文), 'ascii'(只支持英文字符)


# ============================================================
# 5. __name__
# ============================================================
# A. 函数的 __name__
def hello(): pass
print(hello.__name__)   # hello


# B. 类的 __name__
class World: pass
print(World.__name__)   # World


# C. 经典入口写法
def main(): print("程序主入口执行")
if __name__ == "__main__":  # 只有直接运行当前文件时才会执行 main
    main()

# 1. 直接运行当前文件: python this_file.py  print(__name__) 输出: __main__
# 2. 被其他文件 import: import this_file   print(__name__) 输出: this_file