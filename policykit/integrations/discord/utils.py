import datetime
import logging

from django.conf import settings

logger = logging.getLogger(__name__)

def avatar_url(user_info):
    if not user_info['avatar']:
        return None
    return f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}.png"

def get_discord_user_fields(user_info):
    """
    Get DiscordUser fields from Discord user_id
    https://discordpy.readthedocs.io/en/latest/api.html#id7
    """
    return {
        "readable_name": user_info["username"],
        "avatar": avatar_url(user_info),
    }

def should_create_action(message, type=None):
    if type == None:
        logger.debug('type parameter not specified in should_create_action')
        return False

    created_at = None

    if type == "MESSAGE_CREATE":
        from integrations.discord.models import DiscordPostMessage

        # If message already has an object, don't create a new object for it.
        # We only filter on message IDs because they are generated using Twitter
        # snowflakes which are universally unique across all Discord servers.
        if DiscordPostMessage.objects.filter(message_id=message['id']).exists():
            return False

        created_at = message['timestamp'] # ISO8601 timestamp
        created_at = datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%f+00:00")

    if created_at == None:
        logger.debug("created_at is None when it shouldn't be in should_create_action")
        return False

    now = datetime.datetime.now()

    # If action is more than twice the Celery beat frequency seconds old,
    # don't create an object for it. This way, we only create objects for
    # actions taken after PolicyKit has been installed to the community.
    recent_time = 2 * settings.CELERY_BEAT_FREQUENCY
    if now - created_at > datetime.timedelta(seconds=recent_time):
        return False
    return True

def discord_event_to_platform_action(community, outer_event):
    new_api_action = None
    event_type = outer_event["event_type"]
    initiator = outer_event.get("initiator").get("user_id")
    if not initiator:
        return
    event = outer_event["data"]

    from integrations.discord.models import (
        DiscordPostMessage,
        DiscordPostReply,
        DiscordCreateChannel,
        DiscordDeleteChannel,
        DiscordKickUser,
        DiscordBanUser,
        DiscordUnbanUser,
        DiscordUser,
    )

    if event_type == "MESSAGE_CREATE":
        if should_create_action(event, type=event_type):
            new_api_action = DiscordPostMessage()
            new_api_action.community = community
            new_api_action.text = event["content"]
            new_api_action.channel = event["channel"]["id"]
            new_api_action.message = event["id"]
            u, _ = DiscordUser.get_or_create(username=initiator, community=community)
            new_api_action.initiator =  u

    return new_api_action

def start_emoji_vote(policy, action, users=None, post_type="channel", template=None, channel=None):
    # TODO: Implement this function
    pass
