from friendships.models import Friendship
from friendships.services import FriendshipService
from testing.testcases import TestCase


class FriendshipServiceTests(TestCase):

    def setUp(self):
        self.clear_cache()
        self.taotao = self.create_user(username='taotao')
        self.zhuzhu = self.create_user(username='zhuzhu')

    def test_get_followings(self):
        user1 = self.create_user(username='user1')
        user2 = self.create_user(username='user2')
        for to_user in [user1, user2, self.zhuzhu]:
            Friendship.objects.create(from_user=self.taotao, to_user=to_user)

        FriendshipService.invalidate_following_cache(from_user_id=self.taotao.id)
        user_id_set = FriendshipService.get_following_user_id_set(from_user_id=self.taotao.id,)
        self.assertEqual(user_id_set, {user1.id, user2.id, self.zhuzhu.id})

        Friendship.objects.filter(from_user=self.taotao, to_user=self.zhuzhu).delete()

        FriendshipService.invalidate_following_cache(from_user_id=self.taotao.id)
        user_id_set = FriendshipService.get_following_user_id_set(from_user_id=self.taotao.id, )
        self.assertEqual(user_id_set, {user1.id, user2.id,})