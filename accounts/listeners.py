def user_changed(sender, instance, **kwargs):
    from accounts.services import UserService
    UserService.invalidate_user(user_id=instance.id)

def profile_changed(sender, instance, **kwargs):
    from accounts.services import UserService
    UserService.invalidate_profile(user_id=instance.user_id)