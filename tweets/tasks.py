from celery import shared_task
from django.conf import settings

from tweets.constants import TweetModerationStatus


@shared_task(routing_key='llm_tasks')
def moderate_tweet(tweet_id, content):
    if not settings.LLM_MODERATION_ENABLED:
        return 'skipped (LLM moderation disabled)'

    from anthropic import Anthropic
    from tweets.models import Tweet

    client = Anthropic()
    message = client.messages.create(
        model='claude-haiku-4-5',
        max_tokens=10,
        messages=[{
            'role': 'user',
            'content': (
                'Determine whether the following tweet contains abuse, spam, '
                'or other policy-violating content. Reply with only SAFE or '
                f'FLAGGED, no explanation.\n\nTweet content: {content}'
            ),
        }],
    )
    result = message.content[0].text.strip()
    status = (
        TweetModerationStatus.FLAGGED if result == 'FLAGGED'
        else TweetModerationStatus.SAFE
    )

    tweet = Tweet.objects.filter(id=tweet_id).first()
    if tweet is None:
        return result
    Tweet.objects.filter(id=tweet_id).update(moderation_status=status)
    return result
