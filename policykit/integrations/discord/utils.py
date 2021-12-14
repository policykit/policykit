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

    payload = {}

    if users is not None and len(users) > 0:
        if isinstance(users[0], str):
            payload["eligible_voters"] = users
        else:
            payload["eligible_voters"] = [u.username for u in users]

    action = proposal.action
    policy = proposal.policy

    if options:
        payload["poll_type"] = "choice"
        payload["title"] = template or "Please vote"
        payload["options"] = options
    else:
        payload["poll_type"] = "boolean"
        payload["title"] = template or default_boolean_vote_message(policy)

    if channel is not None:
        payload["channel"] = channel
    elif action.kind == PolicyActionKind.PLATFORM and hasattr(action, "channel") and action.channel:
        payload["channel"] = action.channel
    elif action.kind == PolicyActionKind.TRIGGER and hasattr(action, "action") and hasattr(action.action, "channel"):
        payload["channel"] = action.action.channel  # action is a trigger from a governable action
    elif action.action_type == "governableactionbundle":
        first_action = action.bundled_actions.all()[0]
        if hasattr(first_action, "channel") and first_action.channel:
            payload["channel"] = first_action.channel

    if post_type == "channel" and not payload.get("channel"):
        raise Exception("Failed to determine which channel to post in")

    return payload
