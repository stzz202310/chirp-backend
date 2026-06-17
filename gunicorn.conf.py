import multiprocessing

bind = "0.0.0.0:8000"       # Docker 里必须用 0.0.0.0
workers = 2                 # t3.small 内存有限，固定 2 个
timeout = 120
accesslog = "-"             # 访问日志输出到 stdout，docker logs 能看到
errorlog = "-"              # 错误日志同上