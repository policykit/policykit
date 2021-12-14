from django.db import models
from policyengine.models import CommunityPlatform, CommunityUser, TriggerAction
import logging
import requests

from django.db import models
import integrations.discord.utils as DiscordUtils
from policyengine.models import (
    CommunityPlatform,
    CommunityUser,
)

logger = logging.getLogger(__name__)

DISCORD_SLASH_COMMAND_NAME = "policykit"
DISCORD_SLASH_COMMAND_DESCRIPTION = "Send a command to PolicyKit"
DISCORD_SLASH_COMMAND_OPTION = "command"

class DiscordUser(CommunityUser):
    pass


class DiscordCommunity(CommunityPlatform):
    platform = "discord"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def initiate_vote(self, proposal, users=None, post_type="channel", template=None, channel=None):
        DiscordUtils.start_emoji_vote(proposal, users, post_type, template, channel)

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


class DiscordSlashCommand(TriggerAction):
    """
    Command invoked with `/policykit command: "some string value"`
    """

    channel = models.BigIntegerField()
    value = models.TextField()
    interaction_token = models.CharField(max_length=300)


# class DiscordPostMessage(GovernableAction):
#     AUTH = "user"
#     EXECUTE_PARAMETERS = ["text", "channel"]

#     text = models.TextField()
#     channel = models.BigIntegerField()

#     # Recorded so we can later revert post if needed
#     message = models.BigIntegerField()

#     class Meta:
#         permissions = (("can_execute_discordpostmessage", "Can execute discord post message"),)

#     def revert(self):
#         super().revert(call=f"channels/{self.channel}/messages/{self.message}", method="DELETE")

# class DiscordPostReply(GovernableAction):
#     AUTH = "user"
#     EXECUTE_PARAMETERS = ["text", "channel", "message"]

#     text = models.TextField()
#     channel = models.BigIntegerField()
#     message = models.BigIntegerField()

# class DiscordCreateChannel(GovernableAction):
#     AUTH = "user"
#     EXECUTE_PARAMETERS = ["name", "type"]

#     name = models.TextField()
#     # TODO: Convert to enum of choices
#     type = models.TextField()

#     # Recorded so we can later revert channel creation if needed
#     channel = models.BigIntegerField(blank=True)

#     class Meta:
#         permissions = (("can_execute_discordcreatechannel", "Can execute discord create channel"),)

#     def revert(self):
#         super().revert(call=f"channels/{self.channel}/messages", method="DELETE")


# class DiscordDeleteChannel(GovernableAction):
#     AUTH = "user"
#     EXECUTE_PARAMETERS = ["channel"]

#     channel = models.BigIntegerField()

#     class Meta:
#         permissions = (("can_execute_discorddeletechannel", "Can execute discord delete channel"),)


# class DiscordKickUser(GovernableAction):
#     AUTH = "user"
#     EXECUTE_PARAMETERS = ["user"]

#     user = models.BigIntegerField()

#     action_codename = "discordkickuser"
#     readable_name = "kick user"
#     app_name = "discordintegration"

#     class Meta:
#         permissions = (("can_execute_discordkickuser", "Can execute discord kick user"),)


# class DiscordRenameChannel(GovernableAction):
#     channel_id = models.BigIntegerField()
#     name = models.TextField()
#     name_old = models.TextField(blank=True, default="")

#     AUTH = "user"

#     class Meta:
#         permissions = (("can_execute_discordrenamechannel", "Can execute discord rename channel"),)

#     def revert(self):
#         super().revert(values={"name": self.name_old}, call=f"channels/{self.channel_id}", method="PATCH")

#         # Update DiscordChannel object
#         # c = DiscordChannel.objects.filter(channel_id=self.channel_id)
#         # c['channel_name'] = self.name_old
#         # c.save()

#     def execute(self):
#         pass
#         # Execute action if it didn't originate in the community OR it was previously reverted
#         # if not self.community_origin or (self.community_origin and self.community_revert):
#         #     # Retrieve and store old channel name so we can revert the action if necessary
#         #     channel = self.community.make_call(f"channels/{self.channel_id}")
#         #     self.name_old = channel['name']

#         #     # Update the channel name to the new name
#         #     self.community.make_call(f"channels/{self.channel_id}", {'name': self.name}, method='PATCH')

#         #     # Update DiscordChannel object
#         #     c = DiscordChannel.objects.filter(channel_id=self.channel_id)
#         #     c['channel_name'] = self.name
#         #     c.save()


# class DiscordBanUser(GovernableAction):
#     AUTH = "user"
#     EXECUTE_PARAMETERS = ["user"]

#     user = models.BigIntegerField()

#     class Meta:
#         permissions = (("can_execute_discordbanuser", "Can execute discord ban user"),)


# class DiscordUnbanUser(GovernableAction):
#     AUTH = "user"
#     EXECUTE_PARAMETERS = ["user"]

#     user = models.BigIntegerField()

#     class Meta:
#         permissions = (("can_execute_discordunbanuser", "Can execute discord unban user"),)
