"""
memcached: key-value [key, val 都是字符串]

key is 'followings:3'
val is set {1, 2, 5}
1. cache.set: django 会将 set_val 序列化成 字符串val，保存在 memcached 中
2. cache.get: django 会将 memcached 字符串val 取出，反序列化成 set_val

zhuzhu: 'followings:3', 关注了 {1, 2, 5}
高并发的情况下，zhuzhu 关注 6，7 可能会出错
关注 6: read {1, 2 ,5} -> {1, 2, 5, 6} -> write back
关注 7: read {1, 2 ,5} -> {1, 2, 5, 7} -> write back
所以 cache 更新
1. ❌ 直接更新缓存 [高并发时，容易出错]
2. ✅ 让缓存失效 [也可能出错(读的时候，数据库更新了)，概率较低]
web, memcached 在不同的机器上，如果加锁 只能加分布式锁，大大降低访问的效率 [cache就没有意义了]
不加锁 一定会产生数据的不一致

FOLLOWINGS_PATTERN:
1. [明星的]粉丝 数量大
2. [明星的]粉丝 更新快，容易缓存失效"
"""
FOLLOWINGS_PATTERN = 'followings:{user_id}' # key: {user_id}用户的关注列表
USER_PATTERN = 'user:{user_id}'
USER_PROFILE_PATTERN = 'userprofile:{user_id}'
# user_id (not userprofile_id) 是很多表单的外键

# redis