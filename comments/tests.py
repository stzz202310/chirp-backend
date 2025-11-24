from testing.testcases import TestCase


class CommentModelTest(TestCase):

    def setUp(self):
        self.taotao = self.create_user('taotao')
        self.zhuzhu = self.create_user('zhuzhu')
        self.tweet = self.create_tweet(user=self.taotao)
        self.comment = self.create_comment(user=self.taotao, tweet=self.tweet)

    def test_comment(self):
        self.assertNotEquals(self.comment.__str__(), None)

    def test_like_set(self):
        self.create_like(user=self.taotao, target=self.comment)
        self.assertEqual(self.comment.like_set.count(), 1)

        # 重复点赞
        # create_like: Like.objects.create(...) 报错，违反 unique together
        self.create_like(user=self.taotao, target=self.comment)
        self.assertEqual(self.comment.like_set.count(), 1)

        self.create_like(user=self.zhuzhu, target=self.comment)
        self.assertEqual(self.comment.like_set.count(), 2)