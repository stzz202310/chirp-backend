from django.contrib import admin
from tweets.models import Tweet


@admin.register(Tweet)
class TweetAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'   # 筛选
    list_display = (                # 展示
        'created_at',
        'user',
        'content',
    )