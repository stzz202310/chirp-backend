from django.contrib import admin

from tweets.models import Tweet


@admin.register(Tweet)
class TweetAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'   # 数据筛选方式: 必须是时间类型 + 只能指定一个
    list_display = ('created_at', 'user', 'content',)   # 展示