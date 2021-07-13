import json
import logging

import requests
from django.conf import settings
from django.contrib.auth.models import Permission
from django.db import models
import integrations.slack.utils as SlackUtils
from policyengine.models import (
    BooleanVote,
    CommunityPlatform,
    CommunityRole,
    CommunityUser,
    ConstitutionPolicy,
    LogAPICall,
    NumberVote,
    PlatformAction,
    PlatformActionBundle,
    PlatformPolicy,
    Proposal,
    StarterKit,
)

logger = logging.getLogger(__name__)

SLACK_ACTIONS = [
    "slackpostmessage",
    "slackschedulemessage",
    "slackrenameconversation",
    "slackkickconversation",
    "slackjoinconversation",
    "slackpinmessage",
]

SLACK_VIEW_PERMS = [
    "Can view slack post message",
    "Can view slack schedule message",
    "Can view slack rename conversation",
    "Can view slack kick conversation",
    "Can view slack join conversation",
    "Can view slack pin message",
]

SLACK_PROPOSE_PERMS = [
    "Can add slack post message",
    "Can add slack schedule message",
    "Can add slack rename conversation",
    "Can add slack kick conversation",
    "Can add slack join conversation",
    "Can add slack pin message",
]

SLACK_EXECUTE_PERMS = [
    "Can execute slack post message",
    "Can execute slack schedule message",
    "Can execute slack rename conversation",
    "Can execute slack kick conversation",
    "Can execute slack join conversation",
    "Can execute slack pin message",
]

NUMBERS_TEXT = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
}

# Name of generic Slack action in Metagov
# See: https://metagov.policykit.org/redoc/#operation/slack.method
SLACK_METHOD_ACTION = "slack.method"


class SlackUser(CommunityUser):
    pass


class SlackCommunity(CommunityPlatform):
    platform = "slack"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def initiate_vote(self, action, policy, users=None, post_type="channel", template=None, channel=None):
        SlackUtils.start_emoji_vote(policy, action, users, post_type, template, channel)

    def make_call(self, method_name, values={}, action=None, method=None):
        """Called by LogAPICall.make_api_call. Don't change the function signature."""
        response = requests.post(
            f"{settings.METAGOV_URL}/api/internal/action/{method_name}",
            json={"parameters": values},
            headers={"X-Metagov-Community": self.metagov_slug},
        )
        if not response.ok:
            logger.error(f"Error making Slack request {method_name} with params {values}")
            raise Exception(f"{response.status_code} {response.reason} {response.text}")
        if response.content:
            return response.json()
        return None

    def execute_platform_action(self, action, delete_policykit_post=True):
        from policyengine.views import clean_up_proposals

        obj = action

        if not obj.community_origin or (obj.community_origin and obj.community_revert):
            call = obj.ACTION

            data = {}
            admin_user_token = SlackUtils.get_admin_user_token(community=self)

            if hasattr(action, "EXECUTE_PARAMETERS"):
                for fieldname in action.EXECUTE_PARAMETERS:
                    data[fieldname] = getattr(action, fieldname)

            logger.debug(f"Preparing to make request {call} which requires token type {obj.AUTH}...")
            if obj.AUTH == "user":
                data["token"] = action.proposal.author.access_token
                if not data["token"]:
                    # we don't have the token for the user who proposed the action, so use an admin user token instead
                    data["token"] = admin_user_token
            elif obj.AUTH == "admin_bot":
                if action.proposal.author.is_community_admin:
                    data["token"] = action.proposal.author.access_token
            elif obj.AUTH == "admin_user":
                data["token"] = admin_user_token

            logger.debug(f"Overriding token? {True if data.get('token') else False}")

            try:
                self.__make_generic_api_call(call, data)
            except Exception as e:
                logger.error(f"Error making API call in execute_platform_action: {e}")
                clean_up_proposals(action, False)
                raise

            # delete PolicyKit Post
            if delete_policykit_post:
                posted_action = None
                if action.is_bundled:
                    bundle = action.platformactionbundle_set.all()
                    if bundle.exists():
                        posted_action = bundle[0]
                else:
                    posted_action = action

                if posted_action.community_post:
                    values = {
                        "token": admin_user_token,
                        "ts": posted_action.community_post,
                        "channel": obj.channel,
                    }
                    self.__make_generic_api_call("chat.delete", values)

        clean_up_proposals(action, True)

    def handle_metagov_event(self, outer_event):
        """
        Receive Slack Metagov Event for this community
        """
        logger.debug(f"SlackCommunity recieved metagov event: {outer_event['event_type']}")
        if outer_event["initiator"].get("is_metagov_bot") == True:
            logger.debug("Ignoring bot event")
            return

        new_api_action = SlackUtils.slack_event_to_platform_action(self, outer_event)
        if new_api_action is not None:
            new_api_action.community_origin = True
            new_api_action.is_bundled = False
            new_api_action.save()  # save triggers policy evaluation
            logger.debug(f"PlatformAction saved: {new_api_action.pk}")

    def handle_metagov_process(self, process):
        """
        Handle a change to an ongoing Metagov slack.emoji-vote GovernanceProcess.
        This function gets called any time a slack.emoji-vote associated with
        this SlackCommunity gets updated (e.g. if a vote was cast).
        """
        assert process["name"] == "slack.emoji-vote"
        outcome = process["outcome"]
        status = process["status"]  # TODO: handle 'completed' status, which means that process was "closed"
        ts = outcome["message_ts"]
        votes = outcome["votes"]

        action = PlatformAction.objects.filter(community=self, community_post=ts).first()
        action_bundle = PlatformActionBundle.objects.filter(community=self, community_post=ts).first()
        if action is not None:
            # Expect this process to be a boolean vote on an action.
            for (k, v) in votes.items():
                assert k == "yes" or k == "no"
                reaction_bool = True if k == "yes" else False
                for u in v["users"]:
                    user, _ = SlackUser.objects.get_or_create(username=u, community=self)
                    existing_vote = BooleanVote.objects.filter(proposal=action.proposal, user=user).first()
                    if existing_vote is None:
                        logger.debug(f"Casting boolean vote {reaction_bool} by {user} for {action}")
                        BooleanVote.objects.create(proposal=action.proposal, user=user, boolean_value=reaction_bool)
                    elif existing_vote.boolean_value != reaction_bool:
                        logger.debug(f"Casting boolean vote {reaction_bool} by {user} for {action} (vote changed)")
                        existing_vote.boolean_value = reaction_bool
                        existing_vote.save()

        elif action_bundle is not None:
            # Expect this process to be a choice vote on an action bundle.
            bundled_actions = list(action_bundle.bundled_actions.all())
            for (k, v) in votes.items():
                num, voted_action = [(idx, a) for (idx, a) in enumerate(bundled_actions) if str(a) == k][0]
                for u in v["users"]:
                    user, _ = SlackUser.objects.get_or_create(username=u, community=self)
                    existing_vote = NumberVote.objects.filter(proposal=voted_action.proposal, user=user).first()
                    if existing_vote is None:
                        logger.debug(
                            f"Casting number vote {num} by {user} for {voted_action} in bundle {action_bundle}"
                        )
                        NumberVote.objects.create(proposal=voted_action.proposal, user=user, number_value=num)
                    elif existing_vote.number_value != num:
                        logger.debug(
                            f"Casting number vote {num} by {user} for {voted_action} in bundle {action_bundle} (vote changed)"
                        )
                        existing_vote.number_value = num
                        existing_vote.save()

    def post_message(self, text, users=[], post_type="channel", channel=None, thread_ts=None, reply_broadcast=False):
        """
        POST TYPES:
        mpim = multi person message
        im = direct message(s)
        channel = post in channel
        ephemeral = ephemeral post(s) in channel that is only visible to one user
        """
        usernames = [user.username for user in users or []]
        if len(usernames) == 0 and post_type in ["mpim", "im", "ephemeral"]:
            raise Exception(f"user(s) required for post type '{post_type}'")
        if channel is None and post_type in ["channel", "ephemeral"]:
            raise Exception(f"channel required for post type '{post_type}'")

        values = {"text": text}

        if post_type == "mpim":
            # post to group message
            values["users"] = usernames
            response = LogAPICall.make_api_call(self, values, "slack.post-message")
            return [response["ts"]]

        if post_type == "im":
            # message each user individually
            posts = []
            for username in usernames:
                values["users"] = [username]
                response = LogAPICall.make_api_call(self, values, "slack.post-message")
                posts.append(response["ts"])
            return posts

        if post_type == "ephemeral":
            posts = []
            for username in usernames:
                values["user"] = username
                values["channel"] = channel
                response = self.__make_generic_api_call("chat.postEphemeral", values)
                posts.append(response["message_ts"])
            return posts

        if post_type == "channel":
            values["channel"] = channel
            if thread_ts:
                # post message in response as a threaded message reply
                values["thread_ts"] = thread_ts
                values["reply_broadcast"] = reply_broadcast

            response = LogAPICall.make_api_call(self, values, "slack.post-message")
            return [response["ts"]]

        return []

    def __make_generic_api_call(self, method: str, values):
        """Make any Slack method request using Metagov action 'slack.method' """
        cleaned = {k: v for k, v in values.items() if v is not None} if values else {}
        return LogAPICall.make_api_call(self, {"method_name": method, **cleaned}, SLACK_METHOD_ACTION)


class SlackPostMessage(PlatformAction):
    ACTION = "chat.postMessage"
    AUTH = "admin_bot"
    EXECUTE_PARAMETERS = ["text", "channel"]

    text = models.TextField()
    channel = models.CharField("channel", max_length=150)
    timestamp = models.CharField(max_length=32, blank=True)

    action_codename = "slackpostmessage"
    app_name = "slackintegration"

    class Meta:
        permissions = (("can_execute_slackpostmessage", "Can execute slack post message"),)

    def revert(self):
        admin_user_token = SlackUtils.get_admin_user_token(self.community)
        values = {
            "method_name": "chat.delete",
            "token": admin_user_token,
            "ts": self.timestamp,
            "channel": self.channel,
        }
        super().revert(values, SLACK_METHOD_ACTION)


class SlackRenameConversation(PlatformAction):
    ACTION = "conversations.rename"
    AUTH = "admin_user"
    EXECUTE_PARAMETERS = ["channel", "name"]

    name = models.CharField("name", max_length=150)
    channel = models.CharField("channel", max_length=150)
    previous_name = models.CharField(max_length=80)

    action_codename = "slackrenameconversation"
    app_name = "slackintegration"

    class Meta:
        permissions = (("can_execute_slackrenameconversation", "Can execute slack rename conversation"),)

    def revert(self):
        # Slack docs: "only the user that originally created a channel or an admin may rename it"
        values = {
            "method_name": SlackRenameConversation.ACTION,
            "name": self.previous_name,
            "channel": self.channel,
            # Use the initiators access token if we have it (since they already successfully renamed)
            "token": self.initiator.access_token or self.community.__get_admin_user_token(),
        }
        super().revert(values, SLACK_METHOD_ACTION)


class SlackJoinConversation(PlatformAction):
    ACTION = "conversations.invite"
    AUTH = "admin_user"
    EXECUTE_PARAMETERS = ["channel", "users"]

    channel = models.CharField("channel", max_length=150)
    users = models.CharField("users", max_length=15)

    action_codename = "slackjoinconversation"
    app_name = "slackintegration"

    class Meta:
        permissions = (("can_execute_slackjoinconversation", "Can execute slack join conversation"),)

    def revert(self):
        values = {"method_name": "conversations.kick", "user": self.users, "channel": self.channel}
        try:
            super().revert(values, SLACK_METHOD_ACTION)
        except Exception:
            # Whether or not bot can kick is based on workspace settings
            logger.error(f"kick with bot token failed, attempting with admin token")
            values["token"] = self.community.__get_admin_user_token()
            # This will fail with `cant_kick_self` if a user is trying to kick itself.
            # TODO: handle that by using a different token or `conversations.leave` if we have the user's token
            super().revert(values, SLACK_METHOD_ACTION)


class SlackPinMessage(PlatformAction):
    ACTION = "pins.add"
    AUTH = "bot"
    EXECUTE_PARAMETERS = ["channel", "timestamp"]
    channel = models.CharField("channel", max_length=150)
    timestamp = models.CharField(max_length=32)

    action_codename = "slackpinmessage"
    app_name = "slackintegration"

    class Meta:
        permissions = (("can_execute_slackpinmessage", "Can execute slack pin message"),)

    def revert(self):
        values = {"method_name": "pins.remove", "channel": self.channel, "timestamp": self.timestamp}
        super().revert(values, SLACK_METHOD_ACTION)


class SlackScheduleMessage(PlatformAction):
    ACTION = "chat.scheduleMessage"
    EXECUTE_PARAMETERS = ["text", "channel", "post_at"]

    text = models.TextField()
    channel = models.CharField("channel", max_length=150)
    post_at = models.IntegerField("post at")

    action_codename = "slackschedulemessage"
    app_name = "slackintegration"

    class Meta:
        permissions = (("can_execute_slackschedulemessage", "Can execute slack schedule message"),)


class SlackKickConversation(PlatformAction):
    ACTION = "conversations.kick"
    AUTH = "user"
    EXECUTE_PARAMETERS = ["user", "channel"]

    user = models.CharField("user", max_length=15)
    channel = models.CharField("channel", max_length=150)

    action_codename = "slackkickconversation"
    app_name = "slackintegration"

    class Meta:
        permissions = (("can_execute_slackkickconversation", "Can execute slack kick conversation"),)


class SlackStarterKit(StarterKit):
    def init_kit(self, community, creator_token=None):
        for policy in self.genericpolicy_set.all():
            if policy.is_constitution:
                p = ConstitutionPolicy()
                p.community = community
                p.filter = policy.filter
                p.initialize = policy.initialize
                p.check = policy.check
                p.notify = policy.notify
                p.success = policy.success
                p.fail = policy.fail
                p.description = policy.description
                p.name = policy.name

                proposal = Proposal.objects.create(author=None, status=Proposal.PASSED)
                p.proposal = proposal
                p.save()

            else:
                p = PlatformPolicy()
                p.community = community
                p.filter = policy.filter
                p.initialize = policy.initialize
                p.check = policy.check
                p.notify = policy.notify
                p.success = policy.success
                p.fail = policy.fail
                p.description = policy.description
                p.name = policy.name

                proposal = Proposal.objects.create(author=None, status=Proposal.PASSED)
                p.proposal = proposal
                p.save()

        for role in self.genericrole_set.all():
            c = None
            if role.is_base_role:
                c = community.base_role
                role.is_base_role = False
            else:
                c = CommunityRole()
                c.community = community
                c.role_name = role.role_name
                c.name = "Slack: " + community.community_name + ": " + role.role_name
                c.description = role.description
                c.save()

            for perm in role.permissions.all():
                c.permissions.add(perm)

            jsonDec = json.decoder.JSONDecoder()
            perm_set = jsonDec.decode(role.plat_perm_set)

            if "view" in perm_set:
                for perm in SLACK_VIEW_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)
            if "propose" in perm_set:
                for perm in SLACK_PROPOSE_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)
            if "execute" in perm_set:
                for perm in SLACK_EXECUTE_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)

            if role.user_group == "admins":
                group = CommunityUser.objects.filter(community=community, is_community_admin=True)
                for user in group:
                    c.user_set.add(user)
            elif role.user_group == "nonadmins":
                group = CommunityUser.objects.filter(community=community, is_community_admin=False)
                for user in group:
                    c.user_set.add(user)
            elif role.user_group == "all":
                group = CommunityUser.objects.filter(community=community)
                for user in group:
                    c.user_set.add(user)
            elif role.user_group == "creator":
                user = CommunityUser.objects.get(access_token=creator_token)
                c.user_set.add(user)

            c.save()
