import logging
from policyengine.utils import default_boolean_vote_message
from policyengine.models import PolicyActionKind

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


def construct_emoji_vote_params(proposal, users=None, post_type="channel", template=None, channel=None, options=None):
    if post_type not in ["channel"]:
        raise Exception(f"Unsupported post type {post_type}")
    if post_type == "mpim" and not users:
        raise Exception(f"Must pass users for 'mpim' vote")

    params = {}

    if users is not None and len(users) > 0:
        if isinstance(users[0], str):
            params["eligible_voters"] = users
        else:
            params["eligible_voters"] = [u.username for u in users]

    action = proposal.action
    policy = proposal.policy

    if options:
        params["poll_type"] = "choice"
        params["title"] = template or "Please vote"
        params["options"] = options
    else:
        params["poll_type"] = "boolean"
        params["title"] = template or "Please vote"

    if channel is not None:
        params["channel"] = int(channel)
    elif hasattr(action, "channel") and action.channel:
        params["channel"] = action.channel

    if post_type == "channel" and not params.get("channel"):
        raise Exception("Failed to determine which channel to post in")

    return params
