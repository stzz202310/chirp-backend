from datetime import datetime
import pytz


def utc_now():
    return datetime.utcnow().replace(tzinfo=pytz.utc)