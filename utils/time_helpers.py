from django.utils import timezone


def utc_now():
    # 在 twitter.settings 中设置 USE_TZ = True,
    # timezone.now() 会返回一个 UTC 时间
    return timezone.now()