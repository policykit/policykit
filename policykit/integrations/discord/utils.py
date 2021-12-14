import datetime
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def avatar_url(user_info):
    if not user_info["avatar"]:
        return None
    return f"https://cdn.discordapp.com/avatars/{user_info['id']}/{user_info['avatar']}.png"


def get_discord_user_fields(user_info):
    """
    Get DiscordUser fields from Discord's User object
    """
    return {
        "readable_name": user_info["username"],
        "avatar": avatar_url(user_info),
    }


def start_emoji_vote(proposal, users=None, post_type="channel", template=None, channel=None):
    # TODO: Implement this function
    pass
