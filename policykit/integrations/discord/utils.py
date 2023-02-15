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


def infer_channel(proposal):
    """
    If this proposal was initiated by an action on slack, get the channel where it occurred
    """
    action = proposal.action
    if not action.community.platform == "discord":
        # the action occurred off discord, so we can't guess the channel
        return None
    if hasattr(action, "channel") and action.channel:
        return action.channel
    if action.kind == PolicyActionKind.TRIGGER and hasattr(action, "action") and hasattr(action.action, "channel"):
        # action is a trigger from a governable action
        return action.action.channel
    return None


def construct_vote_params(proposal, users=None, post_type="channel", text=None, channel=None, options=None):
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

    if options:
        params["poll_type"] = "choice"
        params["title"] = text or "Please vote"
        params["options"] = options
    else:
        params["poll_type"] = "boolean"
        params["title"] = text or "Please vote"

    if post_type == "channel":
        channel = channel or infer_channel(proposal)
        if not channel:
            raise Exception("Failed to determine which channel to post in")
        params["channel"] = int(channel)

    return params
