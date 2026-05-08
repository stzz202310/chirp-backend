from django.contrib import admin

from tweets.models import Tweet, TweetPhoto


@admin.register(Tweet)
class TweetAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'   # 数据筛选方式: 必须是时间类型 + 只能指定一个
    list_display = ('created_at', 'user', 'content',)


@admin.register(TweetPhoto)
class TweetPhotoAdmin(admin.ModelAdmin):
    list_display = (
        'tweet',
        'user',
        'file',
        'status',
        'has_deleted',
        'deleted_at',
        'created_at',
    )
    list_filter = ('status', 'has_deleted',)
    date_hierarchy = 'created_at'