from django.db import models
from policyengine.models import CommunityPlatform, CommunityUser, GovernableAction
from policykit.settings import DISCORD_BOT_TOKEN
import requests
import json
import logging
import requests

from django.conf import settings
from django.contrib.auth.models import Permission
from django.db import models
import integrations.discord.utils as DiscordUtils
from policyengine.models import (
    BooleanVote,
    CommunityPlatform,
    CommunityRole,
    CommunityUser,
    Policy,
    LogAPICall,
    NumberVote,
    Proposal,
)

logger = logging.getLogger(__name__)


class DiscordUser(CommunityUser):
    pass


class DiscordCommunity(CommunityPlatform):
    platform = "discord"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def initiate_vote(self, proposal, users=None, post_type="channel", template=None, channel=None):
        DiscordUtils.start_emoji_vote(proposal, users, post_type, template, channel)

    def post_message(self, text, channel):
        return self.metagov_plugin.post_message(text=text, channel=channel)



class DiscordUser(CommunityUser):
    pass


class DiscordPostMessage(GovernableAction):
    AUTH = "user"
    EXECUTE_PARAMETERS = ["text", "channel"]

    text = models.TextField()
    channel = models.BigIntegerField()

    # Recorded so we can later revert post if needed
    message = models.BigIntegerField()

    class Meta:
        permissions = (("can_execute_discordpostmessage", "Can execute discord post message"),)

    def revert(self):
        super().revert(call=f"channels/{self.channel}/messages/{self.message}", method="DELETE")


class DiscordPostReply(GovernableAction):
    AUTH = "user"
    EXECUTE_PARAMETERS = ["text", "channel", "message"]

    text = models.TextField()
    channel = models.BigIntegerField()
    message = models.BigIntegerField()

class DiscordCreateChannel(GovernableAction):
    AUTH = "user"
    EXECUTE_PARAMETERS = ["name", "type"]

    name = models.TextField()
    # TODO: Convert to enum of choices
    type = models.TextField()

    # Recorded so we can later revert channel creation if needed
    channel = models.BigIntegerField(blank=True)

    class Meta:
        permissions = (("can_execute_discordcreatechannel", "Can execute discord create channel"),)

    def revert(self):
        super().revert(call=f"channels/{self.channel}/messages", method="DELETE")


class DiscordDeleteChannel(GovernableAction):
    AUTH = "user"
    EXECUTE_PARAMETERS = ["channel"]

    channel = models.BigIntegerField()

    class Meta:
        permissions = (("can_execute_discorddeletechannel", "Can execute discord delete channel"),)


class DiscordKickUser(GovernableAction):
    AUTH = "user"
    EXECUTE_PARAMETERS = ["user"]

    user = models.BigIntegerField()

    action_codename = "discordkickuser"
    readable_name = "kick user"
    app_name = "discordintegration"

    class Meta:
        permissions = (("can_execute_discordkickuser", "Can execute discord kick user"),)


class DiscordRenameChannel(GovernableAction):
    channel_id = models.BigIntegerField()
    name = models.TextField()
    name_old = models.TextField(blank=True, default="")

    AUTH = "user"

    class Meta:
        permissions = (("can_execute_discordrenamechannel", "Can execute discord rename channel"),)

    def revert(self):
        super().revert(values={"name": self.name_old}, call=f"channels/{self.channel_id}", method="PATCH")

        # Update DiscordChannel object
        # c = DiscordChannel.objects.filter(channel_id=self.channel_id)
        # c['channel_name'] = self.name_old
        # c.save()

    def execute(self):
        pass
        # Execute action if it didn't originate in the community OR it was previously reverted
        # if not self.community_origin or (self.community_origin and self.community_revert):
        #     # Retrieve and store old channel name so we can revert the action if necessary
        #     channel = self.community.make_call(f"channels/{self.channel_id}")
        #     self.name_old = channel['name']

        #     # Update the channel name to the new name
        #     self.community.make_call(f"channels/{self.channel_id}", {'name': self.name}, method='PATCH')

        #     # Update DiscordChannel object
        #     c = DiscordChannel.objects.filter(channel_id=self.channel_id)
        #     c['channel_name'] = self.name
        #     c.save()


class DiscordBanUser(GovernableAction):
    AUTH = "user"
    EXECUTE_PARAMETERS = ["user"]

    user = models.BigIntegerField()

    class Meta:
        permissions = (("can_execute_discordbanuser", "Can execute discord ban user"),)


class DiscordUnbanUser(GovernableAction):
    AUTH = "user"
    EXECUTE_PARAMETERS = ["user"]

    user = models.BigIntegerField()

    class Meta:
        permissions = (("can_execute_discordunbanuser", "Can execute discord unban user"),)
