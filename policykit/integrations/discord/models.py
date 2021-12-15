from django.db import models
from policyengine.models import CommunityPlatform, CommunityUser, TriggerAction
import logging

from django.db import models
import integrations.discord.utils as DiscordUtils
from policyengine.models import (
    CommunityPlatform,
    CommunityUser,
)
from policyengine.metagov_app import metagov

logger = logging.getLogger(__name__)

DISCORD_SLASH_COMMAND_NAME = "policykit"
DISCORD_SLASH_COMMAND_DESCRIPTION = "Send a command to PolicyKit"
DISCORD_SLASH_COMMAND_OPTION = "command"


class DiscordUser(CommunityUser):
    pass


class DiscordCommunity(CommunityPlatform):
    platform = "discord"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def initiate_vote(self, proposal, users=None, post_type="channel", template=None, channel=None, options=None):
        # construct args
        args = DiscordUtils.construct_emoji_vote_params(proposal, users, post_type, template, channel, options)
        logger.debug(args)
        # get plugin instance
        plugin = metagov.get_community(self.community.metagov_slug).get_plugin("discord", self.team_id)
        # start process
        process = plugin.start_process("vote", **args)
        # save reference to process on the proposal, so we can link up the signals later
        proposal.governance_process = process
        proposal.community_post = process.outcome["message_id"]
        logger.debug(f"Saving proposal with community_post '{proposal.community_post}'")
        proposal.save()

    def post_message(self, text, channel):
        return self.metagov_plugin.post_message(text=text, channel=channel)

    def _update_or_create_user(self, user_data):
        """
        Helper for creating/updating DiscordUsers. The 'username' field must be unique for Django,
        so it is a string concatenation of the user id and the guild id.

        user_data is a User object https://discord.com/developers/docs/resources/user#user-object

        https://discord.com/developers/docs/resources/guild#guild-member-object
        """
        user_id = user_data["id"]
        unique_username = f"{user_id}:{self.team_id}"
        user_fields = DiscordUtils.get_discord_user_fields(user_data)
        defaults = {k: v for k, v in user_fields.items() if v is not None}
        return DiscordUser.objects.update_or_create(username=unique_username, community=self, defaults=defaults)

    def _get_or_create_user(self, user_id):
        unique_username = f"{user_id}:{self.team_id}"
        return DiscordUser.objects.get_or_create(username=unique_username, community=self)


class DiscordSlashCommand(TriggerAction):
    """
    Command invoked with `/policykit command: "some string value"`

    This is a generic slash command to trigger a policy from Discord.
    """

    channel = models.BigIntegerField()
    value = models.TextField()
    interaction_token = models.CharField(max_length=300)
