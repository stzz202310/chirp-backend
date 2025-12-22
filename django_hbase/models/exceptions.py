class BadRowKeyError(Exception):
    pass


class EmptyColumnError(Exception):
    # raise Exception("column is empty")
    # raise EmptyColumnError("column is empty")
    # 自定义异常: 代码可读性更强; 可以在 except 中被精确捕获
    pass