from django.conf import settings
import logging
import requests
from policyengine.models import PlatformActionBundle, LogAPICall
import datetime
import json
from django.db.models import Q
from policyengine.utils import ActionKind

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


def is_policykit_action(community, test_a, test_b, api_name):
    current_time_minus = datetime.datetime.now() - datetime.timedelta(seconds=2)

    logs = LogAPICall.objects.filter(community=community, proposal_time__gte=current_time_minus).filter(
        Q(call_type=api_name) | Q(call_type="slack.method")
    )
    if logs.exists():
        # logger.debug(f"Made {logs.count()} calls to {api_name} in the last 2 seconds")
        for log in logs:
            j_info = json.loads(log.extra_info)
            # logger.debug(j_info)
            if log.call_type == "slack.method" and j_info.get("method_name") != api_name:
                # if this was a generic API call, the method_name must match the provided api_name
                continue
            if test_a == j_info[test_b]:
                return True

    return False


def get_admin_user_token(community):
    """Get admin token for a user that installed PolicyKit to this Slack org"""
    from integrations.slack.models import SlackUser

    admin_users = SlackUser.objects.filter(community=community, is_community_admin=True, access_token__isnull=False)
    if admin_users.first() is not None:
        return admin_users.first().access_token
    return None


def slack_event_to_platform_action(community, outer_event):
    new_api_action = None
    event_type = outer_event["event_type"]
    initiator = outer_event.get("initiator").get("user_id")
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

    event = outer_event["data"]
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


def start_emoji_vote(evaluation, users=None, post_type="channel", template=None, channel=None):
    payload = {"callback_url": f"{settings.SERVER_URL}/metagov/internal/outcome/{evaluation.pk}"}
    if channel is not None:
        payload["channel"] = channel
    if users is not None and len(users) > 0:
        if isinstance(users[0], str):
            payload["users"] = users
        else:
            payload["users"] = [u.username for u in users]

    action = evaluation.action
    policy = evaluation.policy

    if action.action_type_new == "platformactionbundle" and action.bundle_type == PlatformActionBundle.ELECTION:
        payload["poll_type"] = "choice"
        payload["title"] = template or default_election_vote_message(policy)
        payload["options"] = [str(a) for a in action.bundled_actions.all()]
    else:
        payload["poll_type"] = "boolean"
        payload["title"] = template or default_boolean_vote_message(policy)

    if channel is None and users is None:
        # Determine which channel to post in
        if post_type == "channel":
            if action.action_kind == ActionKind.PLATFORM and hasattr(action, "channel") and action.channel:
                payload["channel"] = action.channel
            elif action.action_type_new == "platformactionbundle":
                first_action = action.bundled_actions.all()[0]
                if hasattr(first_action, "channel") and first_action.channel:
                    payload["channel"] = first_action.channel

    if payload.get("channel") is None and payload.get("users") is None:
        raise Exception("Failed to determine which channel to post in")

    # Kick off process in Metagov
    logger.debug(f"Starting slack vote on {action} governed by {policy}. Payload: {payload}")
    response = requests.post(
        f"{settings.METAGOV_URL}/api/internal/process/slack.emoji-vote",
        json=payload,
        headers={"X-Metagov-Community": policy.community.metagov_slug},
    )
    if not response.ok:
        raise Exception(f"Error starting process: {response.status_code} {response.reason} {response.text}")
    location = response.headers.get("location")
    if not location:
        raise Exception("Response missing location header")

    # Store location URL of the process, so we can use it to close the Metagov process when policy evaluation "completes"
    evaluation.governance_process_url = f"{settings.METAGOV_URL}{location}"
    evaluation.save()

    # Get the unique 'ts' of the vote post, and return it
    response = requests.get(evaluation.governance_process_url)
    if not response.ok:
        raise Exception(f"{response.status_code} {response.reason} {response.text}")
    process = response.json()
    return process["outcome"]["message_ts"]


def default_election_vote_message(policy):
    return (
        "This action is governed by the following policy: " + policy.description + ". Decide between options below:\n"
    )


def default_boolean_vote_message(policy):
    return (
        "This action is governed by the following policy: "
        + policy.description
        + ". Vote with :thumbsup: or :thumbsdown: on this post."
    )
