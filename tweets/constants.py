class TweetPhotoStatus:
    PENDING = 0     # 用数字，不要用字符串: 方便修改显示值
    APPROVED = 1
    REJECTED = 2


TWEET_PHOTO_STATUS_CHOICES = ( # admin 界面的显示值
    (TweetPhotoStatus.PENDING, 'Pending'),
    (TweetPhotoStatus.APPROVED, 'Approved'),
    (TweetPhotoStatus.REJECTED, 'Rejected'),
)

TWEET_PHOTOS_UPLOAD_LIMIT = 9