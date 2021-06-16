import datetime
import json
import logging
from django.http.response import HttpResponseBadRequest

import requests
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from integrations.slack.models import (
    SlackCommunity,
    SlackJoinConversation,
    SlackPinMessage,
    SlackPostMessage,
    SlackRenameConversation,
    SlackStarterKit,
    SlackUser,
)
from integrations.slack.utils import get_slack_user_fields
from policyengine.models import CommunityRole, LogAPICall, Community, PlatformActionBundle

logger = logging.getLogger(__name__)


NUMBERS = {
    0: "zero",
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
}


def slack_login(request):
    """redirect after metagov has gotten the slack user token"""
    logger.info(f"slack_login")
    logger.info(request.GET)
    user_token = request.GET.get("user_token")
    user_id = request.GET.get("user_id")
    team_id = request.GET.get("team_id")
    user = authenticate(request, user_token=user_token, team_id=team_id, user_id=user_id, platform="slack")
    if user:
        login(request, user)
        response = redirect("/main")
    else:
        response = redirect("/login?error=policykit_not_yet_installed_to_that_community")
    return response


def slack_install(request):
    logger.debug(request.GET)
    expected_state = request.session.get("community_install_state")
    if expected_state is None or request.GET.get("state") is None or (not request.GET.get("state") == expected_state):
        logger.error(f"expected {expected_state}")
        return HttpResponseBadRequest("bad state")

    if request.GET.get("error"):
        logger.error(request.GET.get("error"))
        return redirect("/login?error=cancel")

    # metagov identifier for the "parent community" to install Slack to
    metagov_community_slug = request.GET.get("community")

    # TODO(issue): stop passing user id and token
    user_id = request.GET.get("user_id")
    user_token = request.GET.get("user_token")

    try:
        community = Community.objects.get(metagov_slug=metagov_community_slug)
    except Community.DoesNotExist:
        logger.error(f"community not found: {metagov_community_slug}")
        return redirect("/login?error=cancel")

    # Get team info from Slack
    response = requests.post(
        f"{settings.METAGOV_URL}/api/internal/action/slack.method",
        json={"parameters": {"method_name": "team.info"}},
        headers={"X-Metagov-Community": metagov_community_slug},
    )
    if not response.ok:
        raise Exception(f"Error: {response.status_code} {response.reason} {response.text}")
    data = response.json()
    team = data["team"]
    team_id = team["id"]
    readable_name = team["name"]

    # Set readable_name for Community
    if not community.readable_name:
        community.readable_name = readable_name
        community.save()

    user_group, _ = CommunityRole.objects.get_or_create(
        role_name="Base User", name="Slack: " + readable_name + ": Base User"
    )

    slack_community = SlackCommunity.objects.filter(team_id=team_id).first()
    #FIXME: both these branches need to validate that the `plugin` team ID matches.
    if slack_community is None:
        logger.info(f"Creating new SlackCommunity under {community}")
        slack_community = SlackCommunity.objects.create(
            community=community,
            community_name=readable_name,
            team_id=team_id,
            base_role=user_group,
        )
        user_group.community = slack_community
        user_group.save()

        # get the list of users, create SlackUser object for each user
        logger.info(f"Fetching user list for {slack_community}...")
        response = LogAPICall.make_api_call(slack_community, {}, "users.list")
        for new_user in response["members"]:
            if (not new_user["deleted"]) and (not new_user["is_bot"]) and (new_user["id"] != "USLACKBOT"):
                u, _ = SlackUser.objects.get_or_create(
                    username=new_user["id"],
                    readable_name=new_user["real_name"],
                    avatar=new_user["profile"]["image_24"],
                    is_community_admin=new_user["is_admin"],
                    community=slack_community,
                )
                if user_token and user_id and new_user["id"] == user_id:
                    logger.debug(f"Storing access_token for installing user ({user_id})")
                    u.access_token = user_token
                    u.save()

        context = {
            "starterkits": [kit.name for kit in SlackStarterKit.objects.all()],
            "community_name": slack_community.community_name,
            "creator_token": user_token,
            "platform": "slack",
        }
        return render(request, "policyadmin/init_starterkit.html", context)

    else:
        logger.debug("community already exists, updating name..")
        slack_community.community_name = readable_name
        slack_community.save()
        slack_community.community.readable_name = readable_name
        slack_community.community.save()

        # Delete the newly created community, since it already existed
        logger.debug(f"deleting {community}")
        community.delete()

        # Store token for the user who (re)installed Slack
        if user_token and user_id:
            installer = SlackUser.objects.filter(community=slack_community, username=user_id).first()
            if installer is not None:
                logger.debug(f"Storing access_token for installing user ({user_id})")
                installer.access_token = user_token
                installer.save()
            else:
                logger.debug(f"User '{user_id}' is re-installing but no SlackUser exists for them, creating one..")
                response = slack_community.make_call("users.info", {"user": user_id})
                user_info = response["user"]
                user_fields = get_slack_user_fields(user_info)
                user_fields["password"] = user_token
                user_fields["access_token"] = user_token
                SlackUser.objects.create(
                    community=slack_community,
                    username=user_info["id"],
                    defaults=user_fields,
                )

        return redirect("/login?success=true")


def is_policykit_action(community, test_a, test_b, api_name):
    current_time_minus = datetime.datetime.now() - datetime.timedelta(seconds=2)
    logs = LogAPICall.objects.filter(community=community, proposal_time__gte=current_time_minus, call_type=api_name)

    if logs.exists():
        for log in logs:
            j_info = json.loads(log.extra_info)
            if test_a == j_info[test_b]:
                return True

    return False


def maybe_create_new_api_action(community, outer_event):
    new_api_action = None
    event_type = outer_event["event_type"]
    initiator = outer_event.get("initiator").get("user_id")
    event = outer_event["data"]
    if event_type == "channel_rename":
        if not is_policykit_action(community, event["channel"]["name"], "name", SlackRenameConversation.ACTION):
            new_api_action = SlackRenameConversation()
            new_api_action.community = community
            new_api_action.name = event["channel"]["name"]
            new_api_action.channel = event["channel"]["id"]

            u, _ = SlackUser.objects.get_or_create(username=initiator, community=community)
            new_api_action.initiator = u
            prev_names = new_api_action.get_previous_names()
            new_api_action.prev_name = prev_names[0]

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


def post_policy(policy, action, users=[], post_type="channel", template=None, channel=None):
    if action.action_type == "PlatformActionBundle" and action.bundle_type == PlatformActionBundle.ELECTION:
        policy_message_default = (
            "This action is governed by the following policy: "
            + policy.explanation
            + ". Decide between options below:\n"
        )

        bundled_actions = action.bundled_actions.all()
        for num, a in enumerate(bundled_actions):
            policy_message_default += ":" + NUMBERS[num] + ": " + str(a) + "\n"
    else:
        policy_message_default = (
            "This action is governed by the following policy: "
            + policy.description
            + ". Vote with :thumbsup: or :thumbsdown: on this post."
        )

    if not template:
        policy_message = policy_message_default
    else:
        policy_message = template

    values = {"text": policy_message}

    # mpim = multi person message
    # im each user
    # channel all users
    # channel ephemeral users
    usernames = [user.username for user in users or []]

    if len(usernames) == 0 and post_type in ["im", "ephemeral"]:
        raise Exception(f"user(s) required for post type '{post_type}'")

    if post_type == "mpim":
        # open conversation among participants
        response = LogAPICall.make_api_call(policy.community, {"users": ",".join(usernames)}, "conversations.open")
        channel = response["channel"]["id"]
        # post to group message
        values["channel"] = channel
        response = LogAPICall.make_api_call(policy.community, values, "chat.postMessage")
        action.community_post = response["ts"]
        action.save()

    elif post_type == "im":
        # message each user individually
        for username in usernames:
            response = LogAPICall.make_api_call(policy.community, {"users": username}, "conversations.open")
            channel = response["channel"]["id"]

            # post to direct message
            values["channel"] = channel
            response = LogAPICall.make_api_call(policy.community, values, "chat.postMessage")
            # FIXME: there are several community posts (one per user IM) but not all are persisted
            action.community_post = response["ts"]
            action.save()

    elif post_type == "ephemeral":
        for username in usernames:
            values["user"] = username

            if channel:
                values["channel"] = channel
            else:
                if action.action_type == "PlatformAction":
                    values["channel"] = action.channel
                else:
                    a = action.bundled_actions.all()[0]
                    values["channel"] = a.channel

            response = LogAPICall.make_api_call(policy.community, values, "chat.postEphemeral")
            action.community_post = response["message_ts"]
            action.save()

    elif post_type == "channel":
        # post in channel
        if channel:
            values["channel"] = channel
        else:
            # if channel not specified, post in channel where the action occurred
            if action.action_type == "PlatformAction":
                values["channel"] = action.channel
            else:
                a = action.bundled_actions.all()[0]
                values["channel"] = a.channel

        response = LogAPICall.make_api_call(policy.community, values, "chat.postMessage")
        action.community_post = response["ts"]
        action.save()
