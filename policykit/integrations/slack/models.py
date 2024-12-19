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

    def initiate_vote(self, proposal, users=None, post_type="channel", text=None, channel=None, options=None):
        args = SlackUtils.construct_vote_params(proposal, users, post_type, text, channel, options)

        # get plugin instance
        plugin = metagov.get_community(self.community.metagov_slug).get_plugin("slack", self.team_id)
        # start process
        process = plugin.start_process("emoji-vote", **args)
        # save reference to process on the proposal, so we can link up the signals later
        proposal.governance_process = process
        proposal.vote_post_id = process.outcome["message_ts"]
        logger.debug(f"Saving proposal with vote_post_id '{proposal.vote_post_id}'")
        proposal.save()

    def initiate_advanced_vote(self, proposal, candidates, options, users=None, post_type="channel", title=None, channel=None, details=None):
        args = SlackUtils.construct_select_vote_params(proposal, candidates, options, users, post_type, title, channel, details)

        plugin = metagov.get_community(self.community.metagov_slug).get_plugin("slack", self.team_id)
        # start process
        process = plugin.start_process("advanced-vote", **args)
        # save reference to process on the proposal, so we can link up the signals later
        proposal.governance_process = process
        proposal.vote_post_id = process.outcome["message_ts"]
        logger.debug(f"Saving proposal with vote_post_id '{proposal.vote_post_id}'")
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
                for e in Proposal.objects.filter(action=action):
                    if e.vote_post_id:
                        values = {
                            "token": admin_user_token,
                            "ts": e.vote_post_id,
                            "channel": obj.channel,
                        }
                        self.__make_generic_api_call("chat.delete", values)

    def post_message(
        self, proposal, text, users=None, post_type="channel", channel=None, thread_ts=None, reply_broadcast=False
    ):
        """
        POST TYPES:
        mpim = multi person message
        im = direct message(s)
        channel = post in channel
        ephemeral = ephemeral post(s) in channel that is only visible to one user
        """
        if users and len(users) > 0 and isinstance(users[0], str):
            usernames = users
        else:
            usernames = [user.username for user in users or []]
        if len(usernames) == 0 and post_type in ["mpim", "im", "ephemeral"]:
            raise Exception(f"user(s) required for post type '{post_type}'")

        channel = channel or SlackUtils.infer_channel(proposal)
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

    def get_conversations(self, types=["channel"], types_arg="public_channel"):
        """
            acceptable types are "im", "group", "channel"

            types_arg is the exact `types` arg that's passed to list.conversations
                Allows for asking for private_channel only
        """
        def get_channel_type(channel):
            if channel.get("is_im", False):
                return "im"
            elif channel.get("is_group", False):
                return "group"
            elif channel.get("is_channel", False):
                return "channel"
            else:
                return None

        response = self.__make_generic_api_call("conversations.list", {"types": types_arg})
        return [channel for channel in response["channels"] if get_channel_type(channel) in types]

    def get_real_users(self):
        """
        Get realname and id of all slack workspace members that are not bot and not slackbot
        """
        response = self.__make_generic_api_call("users.list", {})
        members = response['members']
        ret = [{'value': x['id'], 'name': x.get('real_name', '')} for x in members if x['is_bot'] is False and x['name'] != 'slackbot']
        return ret

    def get_users_in_channel(self, channel=None):
        from policyengine.models import CommunityUser
        if channel:
            response = self.__make_generic_api_call("conversations.members", {"channel": channel})
            users = []
            for member in response["members"]:
                user = CommunityUser.objects.filter(community=self, username=member).first()
                if user:
                    users.append(user)
            return users
        else:
            return CommunityUser.objects.filter(community=self)

    def rename_conversation(self, channel, name):
        admin_user_token = SlackUtils.get_admin_user_token(community=self)
        self.metagov_plugin.method("conversations.rename", channel=channel, name=name, token=admin_user_token)

    def kick_conversation(self, channel, user):
        admin_user_token = SlackUtils.get_admin_user_token(community=self)
        self.metagov_plugin.method("conversations.kick", channel=channel, user=user, token=admin_user_token)

    def join_conversation(self, channel, users):
        admin_user_token = SlackUtils.get_admin_user_token(community=self)
        users = ",".join(users)
        self.metagov_plugin.method("conversations.invite", channel=channel, users=users, token=admin_user_token)

class SlackPostMessage(GovernableAction):
    ACTION = "chat.postMessage"
    AUTH = "admin_bot"
    EXECUTE_PARAMETERS = ["text", "channel"]
    ACTION_NAME = "Post Message"
    FILTER_PARAMETERS = [
        {
            "name": "initiator",
            "label": "Initiator",
            "entity": "CommunityUser",
            "prompt": "the user who posted a message on Slack",
            "is_list": False,
            "type": "string",
        },
        {
            "name": "text",
            "label": "Message",
            "entity": "Text",
            "prompt": "the message that was posted on Slack",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "prompt": "the channel where the message was posted",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "timestamp",
            "label": "Time",
            "entity": "Timestamp",
            "prompt": "the timestamp of the posted message",
            "is_list": False,
            "type": "string"
        }
    ]
    EXECUTE_VARIABLES = [
        {
            "name": "text",
            "label": "Message",
            "entity": "Text",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "thread",
            "label": "Thread",
            "entity": "Thread",
            "default": "",
            "is_required": False,
            "prompt": "",
            "type": "string",
            "is_list": False
        }
    ]

    text = models.TextField()
    channel = models.CharField("channel", max_length=150)
    timestamp = models.CharField(max_length=32, blank=True)

    class Meta:
        permissions = (("can_execute_slackpostmessage", "Can execute slack post message"),)

    def _revert(self):
        admin_user_token = SlackUtils.get_admin_user_token(self.community)
        values = {
            "method_name": "chat.delete",
            "token": admin_user_token,
            "ts": self.timestamp,
            "channel": self.channel,
        }
        super()._revert(values=values, call=SLACK_METHOD_ACTION)

    def execution_codes(**kwargs):
        text = kwargs.get("text", "")
        channel = kwargs.get("channel", None)
        if not channel: # when the channel is an empty string
            channel = None
        thread =  kwargs.get("thread", None)
        return f"slack.post_message(text={text}, channel={channel}, thread_ts={thread})"

class SlackRenameConversation(GovernableAction):
    ACTION = "conversations.rename"
    AUTH = "admin_user"
    EXECUTE_PARAMETERS = ["channel", "name"]
    # FILTER_PARAMETERS = {"initiator": "CommunityUser", "name": "Text", "previous_name": "Text", "channel": None}
    ACTION_NAME = "Rename Channel"
    FILTER_PARAMETERS = [
        {
            "name": "initiator",
            "label": "Initiator",
            "entity": "CommunityUser",
            "prompt": "the user who renamed a channel on Slack",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "text",
            "label": "New Name",
            "entity": "Text",
            "prompt": "the new name of the channel",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "previous_name",
            "label": "Old Name",
            "entity": "Text",
            "prompt": "the old name of the channel before being renamed",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "prompt": "the channel that was renamed",
            "is_list": False,
            "type": "string"
        }
    ]
    EXECUTE_VARIABLES = [
        {
            "name": "channel",
            "label": "Renaming channel",
            "entity": "SlackChannel",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "name",
            "label": "New channel name",
            "entity": "Text",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        }
    ]

    name = models.CharField("name", max_length=150)
    channel = models.CharField("channel", max_length=150)
    previous_name = models.CharField(max_length=80)

    class Meta:
        permissions = (("can_execute_slackrenameconversation", "Can execute slack rename conversation"),)

    def _revert(self):
        # Slack docs: "only the user that originally created a channel or an admin may rename it"
        values = {
            "method_name": SlackRenameConversation.ACTION,
            "name": self.previous_name,
            "channel": self.channel,
            # Use the initiators access token if we have it (since they already successfully renamed)
            "token": self.initiator.access_token or SlackUtils.get_admin_user_token(community=self.community),
        }
        super()._revert(values=values, call=SLACK_METHOD_ACTION)

    def execution_codes(**kwargs):
        name = kwargs.get("name", None)
        channel = kwargs.get("channel", None)
        if name and channel:
            return f"slack.rename_conversation(channel={channel}, name={name})"
        else:
            logger.error(f"When generating code for SlackRenameConversation: missing name or channel: {name}, {channel}")


class SlackJoinConversation(GovernableAction):
    ACTION = "conversations.invite"
    AUTH = "admin_user"
    EXECUTE_PARAMETERS = ["channel", "users"]
    # FILTER_PARAMETERS = {"initiator": "CommunityUser", "channel": None, "users": None}
    ACTION_NAME = "Invite User to Channel"
    FILTER_PARAMETERS = [
        {
            "name": "initiator",
            "label": "Invitor",
            "entity": "CommunityUser",
            "prompt": "the user who invited new users to a channel on Slack",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "prompt": "the channel where new users were invited to join",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "users",
            "label": "Invited Users",
            "entity": "CommunityUser",
            "prompt": "the users who were invited to join the channel",
            "is_list": True,
            "type": "string"
        }
    ]
    EXECUTE_VARIABLES = [
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "users",
            "label": "Invited user",
            "entity": "CommunityUser",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        }
    ]

    channel = models.CharField("channel", max_length=150)
    users = models.CharField("users", max_length=15)

    class Meta:
        permissions = (("can_execute_slackjoinconversation", "Can execute slack join conversation"),)

    def _revert(self):
        values = {"method_name": "conversations.kick", "user": self.users, "channel": self.channel}
        try:
            super()._revert(values=values, call=SLACK_METHOD_ACTION)
        except Exception:
            # Whether or not bot can kick is based on workspace settings
            logger.error("kick with bot token failed, attempting with admin token")
            values["token"] = SlackUtils.get_admin_user_token(community=self.community)
            # This will fail with `cant_kick_self` if a user is trying to kick itself.
            # TODO: handle that by using a different token or `conversations.leave` if we have the user's token
            super()._revert(values=values, call=SLACK_METHOD_ACTION)

    def execution_codes(**kwargs):
        channel = kwargs.get("channel", None)
        users = kwargs.get("users", None)
        if channel and users:
            return f"slack.join_conversation(channel={channel}, users={users})"
        else:
            logger.error(f"When generating code for SlackJoinConversation: missing channel or users: {channel}, {users}")

class SlackPinMessage(GovernableAction):
    """
        Slack API use the timestamp of the message (in string format) to identify which message should be pinned in this channel
    """
    ACTION = "pins.add"
    AUTH = "bot"
    EXECUTE_PARAMETERS = ["channel", "timestamp"]
    # FILTER_PARAMETERS = {"initiator": "CommunityUser", "channel": None, "timestamp": "Timestamp"}
    ACTION_NAME = "Pin Message "
    FILTER_PARAMETERS = [
        {
            "name": "initiator",
            "label": "Initiator",
            "entity": "CommunityUser",
            "prompt": "the user who pinned a message on Slack",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "prompt": "the channel where a message was pinned",
            "is_list": False,
            "type": "string"
        }
    ]
    EXECUTE_VARIABLES = [
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "timestamp",
            "label": "Timestamp of the pinned message",
            "entity": "Timestamp",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "timestamp",
            "is_list": False
        }
    ]

    channel = models.CharField("channel", max_length=150)
    timestamp = models.CharField(max_length=32)

    class Meta:
        permissions = (("can_execute_slackpinmessage", "Can execute slack pin message"),)

    def _revert(self):
        values = {"method_name": "pins.remove", "channel": self.channel, "timestamp": self.timestamp}
        super()._revert(values=values, call=SLACK_METHOD_ACTION)


class SlackScheduleMessage(GovernableAction):
    """
        Slack API use the timestamp of the message (an integer) here,
        in contrast to the timestamp (in string format) in SlackPinMessage.
        For the simplicity, we treat all of them as integer by default
        We will convert the timestamp to string when we generate codes for this SlackPinMessage action
    """
    ACTION = "chat.scheduleMessage"
    EXECUTE_PARAMETERS = ["text", "channel", "post_at"]
    # FILTER_PARAMETERS = {"text": "Text", "channel": None, "post_at": "Timestamp"}
    ACTION_NAME = "Schedule Message"
    FILTER_PARAMETERS = [
        {
            "name": "initiator",
            "label": "Initiator",
            "entity": "CommunityUser",
            "prompt": "the user who scheduled a message on Slack",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "text",
            "label": "Message",
            "entity": "Text",
            "prompt": "the message that was scheduled",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "prompt": "the channel where the message was scheduled",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "post_at",
            "label": "Scheduled time",
            "entity": "Timestamp",
            "prompt": "the time when the message was scheduled",
            "is_list": False,
            "type": "timestamp"
        }
    ]
    EXECUTE_VARIABLES = [
        {
            "name": "text",
            "label": "Message",
            "entity": None,
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "post_at",
            "label": "Scheduled time",
            "entity": "Timestamp",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "timestamp",
            "is_list": False
        }
    ]
    text = models.TextField()
    channel = models.CharField("channel", max_length=150)
    post_at = models.IntegerField("post at")

    class Meta:
        permissions = (("can_execute_slackschedulemessage", "Can execute slack schedule message"),)


class SlackKickConversation(GovernableAction):
    ACTION = "conversations.kick"
    AUTH = "user"
    EXECUTE_PARAMETERS = ["user", "channel"]
    # FILTER_PARAMETERS = {"initiator": "CommunityUser", "channel": None, "user": "CommunityUser"}
    ACTION_NAME = "Kick User from Channel"
    FILTER_PARAMETERS = [
        {
            "name": "initiator",
            "label": "Initiator",
            "entity": "CommunityUser",
            "prompt": "the user who kicked another user from a channel on Slack",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "prompt": "the channel where a user was kicked from",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "user",
            "label": "Kicked users",
            "entity": "CommunityUser",
            "prompt": "the user who was kicked from the channel",
            "is_list": False,
            "type": "string"
        }
    ]
    EXECUTE_VARIABLES = [
        {
            "name": "channel",
            "label": "Channel",
            "entity": "SlackChannel",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "user",
            "label": "Kicked users",
            "entity": "CommunityUser",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        }
    ]

    user = models.CharField("user", max_length=15)
    channel = models.CharField("channel", max_length=150)

    class Meta:
        permissions = (("can_execute_slackkickconversation", "Can execute slack kick conversation"),)

    def execution_codes(**kwargs):
        channel = kwargs.get("channel")
        user = kwargs.get("user")
        if channel and user:
            return f"slack.kick_conversation(channel={channel}, user={user})"
        else:
            logger.error(f"When generating codes for SlackKickConversation, missing channel or user: {channel}, {user}")
