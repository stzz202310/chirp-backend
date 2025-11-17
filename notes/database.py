print(1)


"""
MySQL
1. 不要用 JOIN
    a. JOIN 本身并不快 [Web后端需要秒回, 不要用JOIN]
    b. JOIN 必须在同一实例内执行 [同一个 MySQL 进程里, 同一物理机器上]
        当你做了 sharding：
        shard_1：运行 MySQL 实例 #1（存 user 表）
        shard_2：运行 MySQL 实例 #2（存 friendship 表）
        它们是两个不同的实例 (不同进程、不同机器), MySQL 做不到跨实例 JOIN, JOIN 失效

2. 不要用 CASCADE 
    删除一个用户 -> 删除这个用户发的帖子 -> 删除帖子的赞和评论 -> 删除评论的赞 ...

3. DROP FOREIGN KEY CONSTRAINT [TODO]

4. N + 1 Queries: 1个 API request 对应 常数级别的 DB queries [10次]
    例子: newsfeeds.services｜friendships.services
    for 循环 {Query 多次插入}
    
    web (client) <-> db (server) 不同机器 需要数据传输和校验
    假设 通讯时间 10ms，SQL操作时间 1ms
    通讯十次 每次插入一条[错误] = (10 + 1) * 10 = 110 ms
    通讯一次 每次插入十条[正确] = 10 + 1 * 10 = 20 ms

"""