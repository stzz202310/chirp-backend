from testing.testcases import TestCase


class CommentModelTest(TestCase):

    def test_comment(self):
        user = self.create_user('taotao')
        tweet = self.create_tweet(user=user)
        comment = self.create_comment(user=user, tweet=tweet)
        self.assertNotEquals(comment.__str__(), None)