class TweetPhotoStatus:
    PENDING = 0
    APPROVED = 1
    REJECTED = 2


TWEET_PHOTO_STATUS_CHOICES = ( # admin 界面的显示值
    (TweetPhotoStatus.PENDING, 'Pending'),
    (TweetPhotoStatus.APPROVED, 'Approved'),
    (TweetPhotoStatus.REJECTED, 'Rejected'),
)

TWEET_PHOTOS_UPLOAD_LIMIT = 9


class TweetModerationStatus:
    PENDING = 0
    SAFE = 1
    FLAGGED = 2


TWEET_MODERATION_STATUS_CHOICES = (
    (TweetModerationStatus.PENDING, 'Pending'),
    (TweetModerationStatus.SAFE, 'Safe'),
    (TweetModerationStatus.FLAGGED, 'Flagged'),
)