import time
from django.conf import settings
from friendships.models import HBaseFollowing

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
rows = table.scan()
print_rows(rows=rows)

row_key2 = b'1000000000000000:1766605138600027' # b'10.:1766605138600027' {b'cf:to_user_id': b'0000000000000002'}
row_key3 = b'1000000000000000:1766605151784532' # b'10.:1766605151784532' {b'cf:to_user_id': b'0000000000000003'}
row_key4 = b'1000000000000000:1766605151794238' # b'10.:1766605151794238' {b'cf:to_user_id': b'0000000000000004'}
row_key5 = b'1000000000000000:1766605151805109' # b'10.:1766605151805109' {b'cf:to_user_id': b'0000000000000005'}
row_key6 = b'1000000000000000:1766605151811393' # b'10.:1766605151811393' {b'cf:to_user_id': b'0000000000000006'}
row_prefix = b'1000000000000000:'

# 1. 基础范围
rows = table.scan(row_start=row_key2, row_stop=row_key6)                        # [2, 3, 4, 5]
rows = table.scan(row_start=row_key2, row_stop=row_key6, limit=2)               # [2, 3]
rows = table.scan(row_start=row_key6, row_stop=row_key3, reverse=True)          # [6, 5, 4]
rows = table.scan(row_start=row_key6, row_stop=row_key2, limit=2, reverse=True) # [6, 5]

# 2. start == stop → 返回单行
rows = table.scan(row_start=row_key2, row_stop=row_key2)                # [2]
rows = table.scan(row_start=row_key6, row_stop=row_key6, reverse=True)  # [6]

# 3. 省略 row_start
rows = table.scan(row_stop=row_key5)                        # [2, 3, 4]
rows = table.scan(row_stop=row_key2)                        # ⚠️[]
rows = table.scan(row_stop=row_key6, reverse=True)          # ⚠️[]
rows = table.scan(row_stop=row_key2, limit=2, reverse=True) # [6, 5]

# 4. 省略 row_stop
rows = table.scan(row_start=row_key2)                           # [2, 3, 4, 5, 6]
rows = table.scan(row_start=row_key6, limit=2)                  # [6]
rows = table.scan(row_start=row_key6, limit=2, reverse=True)    # [6, 5]
rows = table.scan(row_start=row_key2, limit=2, reverse=True)    # [2]

# 5. row_prefix
rows = table.scan(row_start=row_prefix)                             # [2, 3, 4, 5, 6]
rows = table.scan(row_stop=row_prefix)                              # ⚠️ []
rows = table.scan(row_prefix = row_prefix, limit = 2)               # [2, 3]
rows = table.scan(row_prefix = row_prefix, limit = 2, reverse=True) # [6, 5]

HBaseFollowing.drop_table()