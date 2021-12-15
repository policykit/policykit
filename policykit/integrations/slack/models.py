import logging

from django.db import models
import integrations.slack.utils as SlackUtils
from policyengine.models import (
    LogAPICall,
    CommunityPlatform,
    CommunityUser,
    GovernableAction,
    Proposal,
)
from policyengine.metagov_app import metagov

logger = logging.getLogger(__name__)


# Name of generic Slack action in Metagov
# See: https://metagov.policykit.org/redoc/#operation/slack.method
SLACK_METHOD_ACTION = "slack.method"


class SlackUser(CommunityUser):
    pass


class SlackCommunity(CommunityPlatform):
    platform = "slack"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def initiate_vote(self, proposal, users=None, post_type="channel", template=None, channel=None, options=None):
        args = SlackUtils.construct_vote_params(proposal, users, post_type, template, channel, options)

        # get plugin instance
        plugin = metagov.get_community(self.community.metagov_slug).get_plugin("slack", self.team_id)
        # start process
        process = plugin.start_process("emoji-vote", **args)
        # save reference to process on the proposal, so we can link up the signals later
        proposal.governance_process = process
        proposal.community_post = process.outcome["message_ts"]
        logger.debug(f"Saving proposal with community_post '{proposal.community_post}'")
        proposal.save()

    def _execute_platform_action(self, action, delete_policykit_post=False):
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
                data["token"] = action.initiator.access_token if action.initiator else None
                if not data["token"]:
                    # we don't have the token for the user who proposed the action, so use an admin user token instead
                    data["token"] = admin_user_token
            elif obj.AUTH == "admin_bot":
                if action.initiator and action.initiator.is_community_admin:
                    data["token"] = action.initiator.access_token
            elif obj.AUTH == "admin_user":
                data["token"] = admin_user_token

            logger.debug(f"Overriding token? {True if data.get('token') else False}")

            try:
                self.__make_generic_api_call(call, data)
            except Exception as e:
                logger.error(f"Error making API call in _execute_platform_action: {e}")
                raise

            # delete PolicyKit Post
            if delete_policykit_post:
                posted_action = None
                if action.is_bundled:
                    bundle = action.governableactionbundle_set.all()
                    if bundle.exists():
                        posted_action = bundle[0]
                else:
                    posted_action = action

                for e in Proposal.objects.filter(action=posted_action):
                    if e.community_post:
                        values = {
                            "token": admin_user_token,
                            "ts": e.community_post,
                            "channel": obj.channel,
                        }
                        self.__make_generic_api_call("chat.delete", values)

    def post_message(self, text, users=None, post_type="channel", channel=None, thread_ts=None, reply_broadcast=False):
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
            response = self.metagov_plugin.post_message(**values)
            return [response["ts"]]

        if post_type == "im":
            # message each user individually
            posts = []
            for username in usernames:
                values["users"] = [username]
                response = self.metagov_plugin.post_message(**values)
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

            response = self.metagov_plugin.post_message(**values)
            return [response["ts"]]

        return []

    def __make_generic_api_call(self, method: str, values):
        """Make any Slack method request using Metagov action 'slack.method' """
        cleaned = {k: v for k, v in values.items() if v is not None} if values else {}

        # Use LogAPICall so the API call is recorded in the database. This gets used by the `is_policykit_action` helper to determine,
        # in the next few seconds when we receive an event, that this call was initiated by PolicyKIt- NOT a user- so we shouldn't govern it.
        return LogAPICall.make_api_call(self, values={"method_name": method, **cleaned}, call=method)

    def make_call(self, method_name, values={}, action=None, method=None):
        """Called by LogAPICall.make_api_call. Don't change the function signature."""
        if not values.get("method_name"):
            raise Exception("must provide method_name in values to slack make_call")
        return self.metagov_plugin.method(**values)


class SlackPostMessage(GovernableAction):
    ACTION = "chat.postMessage"
    AUTH = "admin_bot"
    EXECUTE_PARAMETERS = ["text", "channel"]

    text = models.TextField()
    channel = models.CharField("channel", max_length=150)
    timestamp = models.CharField(max_length=32, blank=True)

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
        super().revert(values=values, call=SLACK_METHOD_ACTION)


class SlackRenameConversation(GovernableAction):
    ACTION = "conversations.rename"
    AUTH = "admin_user"
    EXECUTE_PARAMETERS = ["channel", "name"]

    name = models.CharField("name", max_length=150)
    channel = models.CharField("channel", max_length=150)
    previous_name = models.CharField(max_length=80)

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
        super().revert(values=values, call=SLACK_METHOD_ACTION)


class SlackJoinConversation(GovernableAction):
    ACTION = "conversations.invite"
    AUTH = "admin_user"
    EXECUTE_PARAMETERS = ["channel", "users"]

    channel = models.CharField("channel", max_length=150)
    users = models.CharField("users", max_length=15)

    class Meta:
        permissions = (("can_execute_slackjoinconversation", "Can execute slack join conversation"),)

    def revert(self):
        values = {"method_name": "conversations.kick", "user": self.users, "channel": self.channel}
        try:
            super().revert(values=values, call=SLACK_METHOD_ACTION)
        except Exception:
            # Whether or not bot can kick is based on workspace settings
            logger.error(f"kick with bot token failed, attempting with admin token")
            values["token"] = self.community.__get_admin_user_token()
            # This will fail with `cant_kick_self` if a user is trying to kick itself.
            # TODO: handle that by using a different token or `conversations.leave` if we have the user's token
            super().revert(values=values, call=SLACK_METHOD_ACTION)


class SlackPinMessage(GovernableAction):
    ACTION = "pins.add"
    AUTH = "bot"
    EXECUTE_PARAMETERS = ["channel", "timestamp"]
    channel = models.CharField("channel", max_length=150)
    timestamp = models.CharField(max_length=32)

    class Meta:
        permissions = (("can_execute_slackpinmessage", "Can execute slack pin message"),)

    def revert(self):
        values = {"method_name": "pins.remove", "channel": self.channel, "timestamp": self.timestamp}
        super().revert(values=values, call=SLACK_METHOD_ACTION)


class SlackScheduleMessage(GovernableAction):
    ACTION = "chat.scheduleMessage"
    EXECUTE_PARAMETERS = ["text", "channel", "post_at"]

    text = models.TextField()
    channel = models.CharField("channel", max_length=150)
    post_at = models.IntegerField("post at")

    class Meta:
        permissions = (("can_execute_slackschedulemessage", "Can execute slack schedule message"),)


class SlackKickConversation(GovernableAction):
    ACTION = "conversations.kick"
    AUTH = "user"
    EXECUTE_PARAMETERS = ["user", "channel"]

    user = models.CharField("user", max_length=15)
    channel = models.CharField("channel", max_length=150)

    class Meta:
        permissions = (("can_execute_slackkickconversation", "Can execute slack kick conversation"),)
