import time
from django.conf import settings
from friendships.hbase_models import HBaseFollowing

def ts_now():
    return int(time.time() * 1000000)

def print_rows(rows):
    for row_key, row_data in rows:
        print(row_key, row_data)

settings.TESTING = True
HBaseFollowing.create_table()
for i in range(2, 7):
    HBaseFollowing.create(from_user_id=1, to_user_id=i, created_at=ts_now())
table = HBaseFollowing.get_table()

"""
table.scan()
方法 1 row_start 和 row_stop (limit, reverse)

row_start   row_stop
✅           ✅           [row_start,   row_stop)
✅           ❌           [row_start,   last row key]
❌           ✅           [1st row key, row_stop)
❌           ❌           [1st row key, last row key] ⚠️full table scan

row_start: 从{row_start} 开始扫描
row_stop:  到{row_stop-1}结束扫描
reverse = True:  i-- 向前扫描(start > stop);    for i in range(row_start, row_stop, -1)
reverse = False: i++ 向后扫描(start < stop);    for i in range(row_start, row_stop)
reverse = False: start > stop 不进入循环, return []; ⚠️start = stop 时, 返回 row[start|end]


方法 2 row_prefix: only rows with row keys matching the prefix will be returned.
                  If given, row_start and row_stop cannot be used.
"""
rows = table.scan()
print_rows(rows=rows)
# This method returns an iterable that can be used for looping over the matching rows.
# b'1000000000000000:1766605138600027' {b'cf:to_user_id': b'0000000000000002'}
# b'1000000000000000:1766605151784532' {b'cf:to_user_id': b'0000000000000003'}
# b'1000000000000000:1766605151794238' {b'cf:to_user_id': b'0000000000000004'}
# b'1000000000000000:1766605151805109' {b'cf:to_user_id': b'0000000000000005'}
# b'1000000000000000:1766605151811393' {b'cf:to_user_id': b'0000000000000006'}

row_key2 = b'1000000000000000:1766605138600027'
row_key3 = b'1000000000000000:1766605151784532'
row_key4 = b'1000000000000000:1766605151794238'
row_key5 = b'1000000000000000:1766605151805109'
row_key6 = b'1000000000000000:1766605151811393'
row_prefix = b'1000000000000000:'


rows = table.scan(row_start=row_key2, row_stop=row_key6)                        # [2, 3, 4, 5]
rows = table.scan(row_start=row_key2, row_stop=row_key6, limit=2)               # [2, 3]
rows = table.scan(row_start=row_key6, row_stop=row_key3, reverse=True)          # [6, 5, 4]
rows = table.scan(row_start=row_key6, row_stop=row_key2, limit=2, reverse=True) # [6, 5]

rows = table.scan(row_start=row_key2, row_stop=row_key2)                # [2]
rows = table.scan(row_start=row_key6, row_stop=row_key6, reverse=True)  # [6]
rows = table.scan(row_start=row_prefix)                                 # [2, 3, 4, 5, 6]
rows = table.scan(row_stop=row_prefix)                                  # ⚠️ []

rows = table.scan(row_start=row_key2)                           # [2, 3, 4, 5, 6]
rows = table.scan(row_start=row_key6, limit=2)                  # [6]
rows = table.scan(row_start=row_key6, limit=2, reverse=True)    # [6, 5]
rows = table.scan(row_start=row_key2, limit=2, reverse=True)    # [2]

rows = table.scan(row_stop=row_key5)                        # [2, 3, 4]
rows = table.scan(row_stop=row_key2, limit=2)               # ⚠️[]
rows = table.scan(row_stop=row_key2, limit=2, reverse=True) # [6, 5]
rows = table.scan(row_stop=row_key6, limit=2, reverse=True) # ⚠️[]

rows = table.scan(row_prefix = row_prefix, limit = 2)               # [2, 3]
rows = table.scan(row_prefix = row_prefix, limit = 2, reverse=True) # [6, 5]


HBaseFollowing.drop_table()