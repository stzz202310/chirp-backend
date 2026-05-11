import datetime
import decimal
import uuid

from django.core.serializers.json import DjangoJSONEncoder
from django.utils.duration import duration_iso_string
from django.utils.functional import Promise
from django.utils.timezone import is_aware


class JSONEncoder(DjangoJSONEncoder):
    # JSONEncoder 修改: 保留完整 microsecond (6位)，提升时间精度
    def default(self, o):
        if isinstance(o, datetime.datetime):
            r = o.isoformat()
            # if o.microsecond:
            #     r = r[:23] + r[26:] ← 截取到毫秒，跳过后3位微秒 [23, 24, 25]
            if r.endswith('+00:00'):
                r = r[:-6] + 'Z'
            return r
        elif isinstance(o, datetime.date):
            return o.isoformat()
        elif isinstance(o, datetime.time):
            if is_aware(o):
                raise ValueError("JSON can't represent timezone-aware times.")
            r = o.isoformat()
            if o.microsecond:
                r = r[:12]
            return r
        elif isinstance(o, datetime.timedelta):
            return duration_iso_string(o)
        elif isinstance(o, (decimal.Decimal, uuid.UUID, Promise)):
            return str(o)
        else:
            return super().default(o)