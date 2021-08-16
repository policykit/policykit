from django.db import models
from policyengine.models import CommunityPlatform, CommunityUser, PlatformAction, Policy, Proposal, CommunityRole
from django.contrib.auth.models import Permission, ContentType
from policykit.settings import DISCORD_BOT_TOKEN
import requests
import json
import logging

logger = logging.getLogger(__name__)

DISCORD_ACTIONS = [
    'discordpostmessage',
    'discorddeletemessage',
    'discordrenamechannel',
    'discordcreatechannel',
    'discorddeletechannel'
]

# Storing basic info of Discord channels to prevent repeated calls to Discord
# gateway for channel information.
class DiscordChannel(models.Model):
    guild_id = models.BigIntegerField()
    channel_id = models.BigIntegerField()
    channel_name = models.TextField()

class DiscordCommunity(CommunityPlatform):
    API = 'https://discordapp.com/api/'
    platform = "discord"

    team_id = models.CharField('team_id', max_length=150, unique=True)

    def notify_action(self, *args, **kwargs):
        self.initiate_vote(*args, **kwargs)

    def initiate_vote(self, proposal, users=None, template=None, channel=None):
        from integrations.discord.views import initiate_action_vote
        initiate_action_vote(proposal, users, template, channel)

    def post_message(self, text, channel):
        return self.make_call(f'channels/{channel}/messages', values={'content': text}, method="POST")

    def save(self, *args, **kwargs):
        super(DiscordCommunity, self).save(*args, **kwargs)

        content_types = ContentType.objects.filter(model__in=DISCORD_ACTIONS)
        perms = Permission.objects.filter(content_type__in=content_types, name__contains="can add ")
        for p in perms:
            self.base_role.permissions.add(p)

    def make_call(self, url, values=None, action=None, method="GET"):
        response = requests.request(
            method=method,
            url=self.API + url,
            json=values,
            headers={'Authorization': 'Bot %s' % DISCORD_BOT_TOKEN}
        )
        logger.debug(f"Made request to {response.request.method} {response.request.url} with body {response.request.body}")

        if not response.ok:
            logger.error(f"{response.status_code} {response.reason} {response.text}")
            raise Exception(f"{response.status_code} {response.reason} {response.text}")
        if response.content:
            return response.json()
        return None

class DiscordUser(CommunityUser):
    def save(self, *args, **kwargs):
        super(DiscordUser, self).save(*args, **kwargs)
        group = self.community.base_role
        group.user_set.add(self)

class DiscordPostMessage(PlatformAction):
    channel_id = models.BigIntegerField()
    message_id = models.BigIntegerField()
    text = models.TextField()

    AUTH = 'user'

    class Meta:
        permissions = (
            ('can_execute_discordpostmessage', 'Can execute discord post message'),
        )

    def revert(self):
        super().revert({}, f"channels/{self.channel_id}/messages/{self.message_id}", method='DELETE')

    def execute(self):
        # Execute action if it didn't originate in the community OR it was previously reverted
        if not self.community_origin or (self.community_origin and self.community_revert):
            message = self.community.post_message(text=self.text, channel=self.channel_id)

            self.message_id = message['id']
            self.save()

class DiscordDeleteMessage(PlatformAction):
    channel_id = models.BigIntegerField()
    message_id = models.BigIntegerField()
    text = models.TextField(blank=True, default='')

    AUTH = 'user'

    class Meta:
        permissions = (
            ('can_execute_discorddeletemessage', 'Can execute discord delete message'),
        )

    def revert(self):
        super().revert({'content': self.text}, f"channels/{self.channel_id}/messages")

    def execute(self):
        # Execute action if it didn't originate in the community OR it was previously reverted
        if not self.community_origin or (self.community_origin and self.community_revert):
            # Gets the channel message and stores the text (in case of revert)
            message = self.community.make_call(f"channels/{self.channel_id}/messages/{self.message_id}")
            self.text = message['content']
            self.save()

            # Deletes the message
            self.community.make_call(f"channels/{self.channel_id}/messages/{self.message_id}", method='DELETE')

class DiscordRenameChannel(PlatformAction):
    channel_id = models.BigIntegerField()
    name = models.TextField()
    name_old = models.TextField(blank=True, default='')

    AUTH = 'user'

    class Meta:
        permissions = (
            ('can_execute_discordrenamechannel', 'Can execute discord rename channel'),
        )

    def revert(self):
        super().revert({'name': self.name_old}, f"channels/{self.channel_id}", method='PATCH')

        # Update DiscordChannel object
        c = DiscordChannel.objects.filter(channel_id=self.channel_id)
        c['channel_name'] = self.name_old
        c.save()

    def execute(self):
        # Execute action if it didn't originate in the community OR it was previously reverted
        if not self.community_origin or (self.community_origin and self.community_revert):
            # Retrieve and store old channel name so we can revert the action if necessary
            channel = self.community.make_call(f"channels/{self.channel_id}")
            self.name_old = channel['name']

            # Update the channel name to the new name
            self.community.make_call(f"channels/{self.channel_id}", {'name': self.name}, method='PATCH')

            # Update DiscordChannel object
            c = DiscordChannel.objects.filter(channel_id=self.channel_id)
            c['channel_name'] = self.name
            c.save()

class DiscordCreateChannel(PlatformAction):
    channel_id = models.BigIntegerField(blank=True)
    name = models.TextField()

    AUTH = 'user'

    class Meta:
        permissions = (
            ('can_execute_discordcreatechannel', 'Can execute discord create channel'),
        )

    def revert(self):
        super().revert({}, f"channels/{self.channel_id}", method='DELETE')

    def execute(self):
        # Execute action if it didn't originate in the community OR it was previously reverted
        if not self.community_origin or (self.community_origin and self.community_revert):
            guild_id = self.community.team_id
            channel = self.community.make_call(f"guilds/{guild_id}/channels", {'name': self.name}, method="POST")
            self.channel_id = channel['id']
            self.save()

            # Create a new DiscordChannel object
            DiscordChannel.objects.get_or_create(
                guild_id=guild_id,
                channel_id=self.channel_id,
                channel_name=channel['name']
            )

class DiscordDeleteChannel(PlatformAction):
    channel_id = models.BigIntegerField()

    AUTH = 'user'

    class Meta:
        permissions = (
            ('can_execute_discorddeletechannel', 'Can execute discord delete channel'),
        )

    def execute(self):
        # Execute action if it didn't originate in the community
        if not self.community_origin:
            self.community.make_call(f"channels/{self.channel_id}", method='DELETE')
