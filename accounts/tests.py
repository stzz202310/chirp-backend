from accounts.models import UserProfile
from testing.testcases import TestCase


class UserProfileTests(TestCase):
    def test_profile_property(self):
        taotao = self.create_user(username='taotao')
        self.assertEqual(UserProfile.objects.count(), 0)
        profile = taotao.profile
        # isinstance(obj, Class): obj 是不是 Class 的实例
        self.assertEqual(isinstance(profile, UserProfile), True)
        self.assertEqual(UserProfile.objects.count(), 1)