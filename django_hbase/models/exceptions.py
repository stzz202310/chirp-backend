class BadRowKeyError(Exception):
    pass


class EmptyColumnError(Exception):
    pass

# raise Exception("empty col")          Exception: empty col        抛出的是内置异常 Exception
# raise EmptyColumnError("empty col")   EmptyColumnError: empty col 抛出的是自定义异常 EmptyColumnError(继承自 Exception)
# 自定义异常: 代码可读性更强; 方便区分不同错误类型; 可以精确捕获 "try except EmptyColumnError"