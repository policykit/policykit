import datetime
import json
import logging

from django.db.models import Q
from policyengine.models import LogAPICall, PolicyActionKind
from policyengine.utils import default_boolean_vote_message

logger = logging.getLogger(__name__)


def get_slack_user_fields(user_info):
    """
    Get SlackUser fields from Slack 'user' type

    https://api.slack.com/types/user
    """
    return {
        "username": user_info["id"],
        "readable_name": user_info["profile"]["real_name"],
        "avatar": user_info["profile"]["image_24"],
    }


def is_policykit_action(community, value_to_match, key_to_match, api_name):
    # logger.debug("is_policykit_action", extra={"is_policykit_action.value_to_match": value_to_match, "is_policykit_action.key_to_match": key_to_match, "is_policykit_action.api_name": api_name})
    current_time_minus = datetime.datetime.now() - datetime.timedelta(seconds=2)

    logs = LogAPICall.objects.filter(community=community, proposal_time__gte=current_time_minus).filter(
        Q(call_type=api_name) | Q(call_type="slack.method")
    )
    # logger.debug(f">is_policykit_action: {logs.count()} possible matches for {api_name} with key '{key_to_match}' equal to '{value_to_match}'")
    # logger.debug(f"{list(logs.values_list('extra_info', flat=True))}")
    if logs.exists():
        # logger.debug(f"Made {logs.count()} calls to {api_name} in the last 2 seconds")
        for log in logs:
            j_info = json.loads(log.extra_info)
            if log.call_type == "slack.method" and j_info.get("method_name") != api_name:
                # if this was a generic API call, the method_name must match the provided api_name
                continue
            if value_to_match == j_info[key_to_match]:
                # logger.debug(f">found matching log {log.pk}")
                # logger.debug("is_policykit_action -> True")
                return True
    # logger.debug(f">no match")
    # logger.debug("is_policykit_action -> False")
    return False


def get_admin_user_token(community):
    """Get admin token for a user that installed PolicyKit to this Slack org"""
    from integrations.slack.models import SlackUser

    admin_users = SlackUser.objects.filter(community=community, is_community_admin=True, access_token__isnull=False)
    if admin_users.first() is not None:
        return admin_users.first().access_token
    return None


def slack_event_to_platform_action(community, event_type, data, initiator):
    new_api_action = None
    initiator = initiator.get("user_id")
    if not initiator:
        # logger.debug(f"{event_type} event does not have an initiating user ID, skipping")
        return
    from integrations.slack.models import (
        SlackJoinConversation,
        SlackPinMessage,
        SlackPostMessage,
        SlackRenameConversation,
        SlackUser,
    )

    event = data
    if event_type == "message" and event.get("subtype") == "channel_name":
        if not is_policykit_action(community, event["name"], "name", SlackRenameConversation.ACTION):
            new_api_action = SlackRenameConversation(
                community=community, name=event["name"], channel=event["channel"], previous_name=event["old_name"]
            )
            u, _ = SlackUser.objects.get_or_create(username=initiator, community=community)
            new_api_action.initiator = u
    elif event_type == "message" and event.get("subtype") == None:
        if not is_policykit_action(community, event["text"], "text", SlackPostMessage.ACTION):
            new_api_action = SlackPostMessage()
            new_api_action.community = community
            new_api_action.text = event["text"]
            new_api_action.channel = event["channel"]
            new_api_action.timestamp = event["ts"]

            u, _ = SlackUser.objects.get_or_create(username=initiator, community=community)

            new_api_action.initiator = u

    elif event_type == "member_joined_channel":
        if not is_policykit_action(community, event["channel"], "channel", SlackJoinConversation.ACTION):
            new_api_action = SlackJoinConversation()
            new_api_action.community = community
            if event.get("inviter"):
                u, _ = SlackUser.objects.get_or_create(username=event["inviter"], community=community)
                new_api_action.initiator = u
            else:
                u, _ = SlackUser.objects.get_or_create(username=initiator, community=community)
                new_api_action.initiator = u
            new_api_action.users = initiator
            new_api_action.channel = event["channel"]

    elif event_type == "pin_added":
        if not is_policykit_action(community, event["channel_id"], "channel", SlackPinMessage.ACTION):
            new_api_action = SlackPinMessage()
            new_api_action.community = community

            u, _ = SlackUser.objects.get_or_create(username=initiator, community=community)
            new_api_action.initiator = u
            new_api_action.channel = event["channel_id"]
            new_api_action.timestamp = event["item"]["message"]["ts"]

    return new_api_action


def infer_channel(proposal):
    """
    If this proposal was initiated by an action on slack, get the channel where it occurred
    """
    action = proposal.action
    if not action.community.platform == "slack":
        # the action occurred off slack, so we can't guess the channel
        return None
    if hasattr(action, "channel") and action.channel:
        return action.channel
    if action.kind == PolicyActionKind.TRIGGER and hasattr(action, "action") and hasattr(action.action, "channel"):
        # action is a trigger from a governable action
        return action.action.channel
    return None


def construct_vote_params(proposal, users=None, post_type="channel", text=None, channel=None, options=None):
    from policyengine.models import CommunityUser
    
    if post_type not in ["channel", "mpim"]:
        raise Exception(f"Unsupported post type {post_type}. Must be 'channel' or 'mpim'")
    if post_type == "mpim" and not users:
        raise Exception("Must pass users for 'mpim' vote")

    params = {}

    if users is not None:
        if isinstance(users, str) or isinstance(users, CommunityUser):
            users = [users]

        if isinstance(users[0], str):
            params["eligible_voters"] = users
        else:
            params["eligible_voters"] = [u.username for u in users]

    action = proposal.action
    policy = proposal.policy

    if options:
        params["poll_type"] = "choice"
        params["title"] = text or "Please vote"
        params["options"] = options
    else:
        params["poll_type"] = "boolean"
        params["title"] = text or default_boolean_vote_message(policy)

    if post_type == "channel":
        params["channel"] = channel or infer_channel(proposal)

        if not params["channel"]:
            raise Exception("Failed to determine which channel to post in")

    return params

def construct_select_vote_params(proposal, candidates, options, users=None, post_type="channel", title=None, channel=None, details=None):
    from policyengine.models import CommunityUser
    
    if post_type not in ["channel", "mpim"]:
        raise Exception(f"Unsupported post type {post_type}. Must be 'channel' or 'mpim'")
    if post_type == "mpim" and not users:
        raise Exception("Must pass users for 'mpim' vote")

    params = {}

    if users is not None:
        if isinstance(users, str) or isinstance(users, CommunityUser):
            users = [users]

        if isinstance(users[0], str):
            params["eligible_voters"] = users
        elif isinstance(users[0], CommunityUser):
            params["eligible_voters"] = [u.username for u in users]

    params["options"] = options
    params["candidates"] = candidates

    params["title"] = title or "Please vote"
    params["details"] = details or ""
    
    if post_type == "channel":
        params["channel"] = channel or infer_channel(proposal)

        if not params["channel"]:
            raise Exception("Failed to determine which channel to post in")

    return params
