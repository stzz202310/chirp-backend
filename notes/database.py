print(1)


"""
MySQL
1. 不要用 JOIN       表单相乘 O(n^2), web 需要实时响应
2. CASCADE          删除一个用户 -> 删除这个用户发的帖子 -> 删除帖子的赞和评论 -> 删除评论的赞 ...
3. DROP FOREIGN KEY CONSTRAINT [TODO]
4. N + 1 Queries    for 循环 {Query 多次插入}     newsfeeds.services｜friendships.services

"""