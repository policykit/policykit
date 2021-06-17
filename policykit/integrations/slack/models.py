import json
import logging

import requests
from django.conf import settings
from django.contrib.auth.models import Permission
from django.db import models
from integrations.slack.utils import get_admin_user_token, reaction_to_boolean
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


class SlackUser(CommunityUser):
    pass


class SlackCommunity(CommunityPlatform):
    platform = "slack"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def notify_action(self, action, policy, users=[], post_type="channel", template=None, channel=None):
        from integrations.slack.views import post_policy

        post_policy(policy, action, users, post_type, template, channel)

    def make_call(self, method_name, values={}, action=None, method=None):
        response = requests.post(
            f"{settings.METAGOV_URL}/api/internal/action/slack.method",
            json={"parameters": {"method_name": method_name, **values}},
            headers={"X-Metagov-Community": self.metagov_slug},
        )
        if not response.ok:
            raise Exception(f"Error: {response.status_code} {response.reason} {response.text}")
        if response.content:
            return response.json()
        return None

    def execute_platform_action(self, action, delete_policykit_post=True):
        logger.debug(f">> SlackCommunity.execute_platform_action {action.ACTION} for {action}")
        from policyengine.views import clean_up_proposals

        obj = action

        if not obj.community_origin or (obj.community_origin and obj.community_revert):
            call = obj.ACTION

            data = {}
            if hasattr(action, "EXECUTE_PARAMETERS"):
                for fieldname in action.EXECUTE_PARAMETERS:
                    data[fieldname] = getattr(action, fieldname)

            logger.debug(f"Preparing to make request {call} which requires token type {obj.AUTH}...")
            if obj.AUTH == "user":
                data["token"] = action.proposal.author.access_token
                if not data["token"]:
                    # we don't have the token for the user who proposed the action, so use an admin user token instead
                    admin_user_token = get_admin_user_token(self)
                    if admin_user_token:
                        data["token"] = admin_user_token
            elif obj.AUTH == "admin_bot":
                if action.proposal.author.is_community_admin and action.proposal.author.access_token:
                    data["token"] = action.proposal.author.access_token
            elif obj.AUTH == "admin_user":
                admin_user_token = get_admin_user_token(self)
                if admin_user_token:
                    data["token"] = admin_user_token

            logger.debug(f"Overriding token? {True if data.get('token') else False}")

            try:
                LogAPICall.make_api_call(self, data, call)
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
                    admin_user_token = get_admin_user_token(self)
                    if admin_user_token:
                        values = {
                            "token": admin_user_token,
                            "ts": posted_action.community_post,
                            "channel": obj.channel,
                        }
                        LogAPICall.make_api_call(self, values, "chat.delete")
                    else:
                        logger.error("Can't delete PolicyKit community post, no admin token to use for chat.delete")

        clean_up_proposals(action, True)

    def handle_metagov_event(self, outer_event):
        """
        Receive Slack Metagov Event for this community
        """
        logger.debug(f"SlackCommunity recieved metagov event: {outer_event['event_type']}")
        if outer_event["initiator"].get("is_metagov_bot") == True:
            logger.debug("Ignoring bot event")
            return

        event_type = outer_event["event_type"]
        initiator = outer_event["initiator"].get("user_id")

        from integrations.slack.views import maybe_create_new_api_action

        new_api_action = maybe_create_new_api_action(self, outer_event)

        if new_api_action is not None:
            new_api_action.community_origin = True
            new_api_action.is_bundled = False
            new_api_action.save()  # save triggers policy evaluation
        else:
            logger.debug(f"{event_type}: no PlatformAction created")

        if event_type == "reaction_added":
            event = outer_event["data"]
            ts = event["item"]["ts"]

            # check if this ts corresponds to a community_post action or bundle
            action = PlatformAction.objects.filter(community=self, community_post=ts).first()
            action_bundle = PlatformActionBundle.objects.filter(community=self, community_post=ts).first()
            reaction_bool = reaction_to_boolean(event["reaction"])

            if action is not None and reaction_bool is not None:
                user, _ = SlackUser.objects.get_or_create(username=initiator, community=self)
                logger.debug(f"Processing boolean Slack vote {reaction_bool} by {user}")
                existing_vote = BooleanVote.objects.filter(proposal=action.proposal, user=user).first()
                if existing_vote is not None:
                    existing_vote.boolean_value = reaction_bool
                    existing_vote.save()
                else:
                    BooleanVote.objects.create(proposal=action.proposal, user=user, boolean_value=reaction_bool)

            elif action_bundle is not None and event["reaction"] in NUMBERS_TEXT.keys():
                bundled_actions = list(action_bundle.bundled_actions.all())
                num = NUMBERS_TEXT[event["reaction"]]
                voted_action = bundled_actions[num]
                user, _ = SlackUser.objects.get_or_create(username=initiator, community=self)
                logger.debug(f"Processing numeric Slack vote {num} for action {voted_action} by user {user}")

                existing_vote = NumberVote.objects.filter(proposal=voted_action.proposal, user=user).first()
                if existing_vote is not None:
                    existing_vote.number_value = num
                    existing_vote.save()
                else:
                    NumberVote.objects.create(proposal=voted_action.proposal, user=user, number_value=num)


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
        admin_user_token = get_admin_user_token(self.community)
        if admin_user_token is None:
            raise Exception("No admin access token found")

        values = {"token": admin_user_token, "ts": self.timestamp, "channel": self.channel}
        super().revert(values, "chat.delete")


class SlackRenameConversation(PlatformAction):
    ACTION = "conversations.rename"
    AUTH = "admin_user"
    EXECUTE_PARAMETERS = ["channel", "name"]

    name = models.CharField("name", max_length=150)
    channel = models.CharField("channel", max_length=150)

    action_codename = "slackrenameconversation"
    app_name = "slackintegration"

    class Meta:
        permissions = (("can_execute_slackrenameconversation", "Can execute slack rename conversation"),)

    def get_previous_names(self):
        response = self.community.make_metagov_call("conversations.info", {"channel": self.channel})
        return response["channel"]["previous_names"]

    def revert(self):
        # "only the user that originally created a channel or an admin may rename it"
        # Use the initiating users access token if we have it (since they already successfully renamed)

        # TODO: self.prev_name is not persisted, why? Add a field to the model.
        values = {"name": self.prev_name, "channel": self.channel}
        if self.initiator.access_token:
            values["token"] = self.initiator.access_token
        super().revert(values, "conversations.rename")


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
        admin_user_token = get_admin_user_token(self.community)
        if admin_user_token is None:
            raise Exception("No admin access token found")
        values = {"user": self.users, "token": admin_user_token, "channel": self.channel}
        super().revert(values, "conversations.kick")


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
        values = {"channel": self.channel, "timestamp": self.timestamp}
        super().revert(values, "pins.remove")


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
