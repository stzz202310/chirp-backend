from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from accounts.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'nickname', 'avatar', 'created_at', 'updated_at',)
    date_hierarchy = 'created_at'


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'user_profiles'


class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'is_staff', 'date_joined',)
    date_hierarchy = 'date_joined'
    inlines = (UserProfileInline,)  # 内联编辑: 让 UserProfile 附加到 User 下面一起管理


# Re-register UserAdmin
admin.site.unregister(User)             # 先删除 Django 默认的 UserAdmin
admin.site.register(User, UserAdmin)    # 再注册你自定义的 UserAdmin