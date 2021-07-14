from django.db import models
from policyengine.models import CommunityPlatform, CommunityUser, PlatformAction, StarterKit, ConstitutionPolicy, Proposal, PlatformPolicy, CommunityRole
from django.contrib.auth.models import Permission, ContentType, User
from policykit.settings import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_BOT_TOKEN
import urllib
from urllib import parse
import urllib.request
import urllib.error
import base64
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
    guild_id = models.IntegerField()
    channel_id = models.IntegerField()
    channel_name = models.TextField()

class DiscordCommunity(CommunityPlatform):
    API = 'https://discordapp.com/api/'
    platform = "discord"
    permissions = [
        "discord post message",
        "discord delete message",
        "discord rename channel",
        "discord create channel",
        "discord delete channel"
    ]

    team_id = models.CharField('team_id', max_length=150, unique=True)

    def notify_action(self, action, policy, users=None, template=None, channel=None):
        from integrations.discord.views import post_policy
        post_policy(policy, action, users, template, channel)

    def save(self, *args, **kwargs):
        super(DiscordCommunity, self).save(*args, **kwargs)

        content_types = ContentType.objects.filter(model__in=DISCORD_ACTIONS)
        perms = Permission.objects.filter(content_type__in=content_types, name__contains="can add ")
        for p in perms:
            self.base_role.permissions.add(p)

    def make_call(self, url, values=None, action=None, method=None):
        data = None
        if values:
            data = urllib.parse.urlencode(values)
            data = data.encode('utf-8')

        req = urllib.request.Request(self.API + url, data, method=method)
        req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason

        try:
            resp = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            logger.error('reached HTTPError')
            logger.error(e.code)
            error_message = e.read()
            logger.error(error_message)
            raise

        res = resp.read().decode('utf-8')
        if res:
            return json.loads(res)
        return None

class DiscordUser(CommunityUser):
    def save(self, *args, **kwargs):
        super(DiscordUser, self).save(*args, **kwargs)
        group = self.community.base_role
        group.user_set.add(self)

class DiscordPostMessage(PlatformAction):
    channel_id = models.IntegerField()
    message_id = models.IntegerField()
    text = models.TextField()

    ACTION = f"channels/{channel_id}/messages"
    AUTH = 'user'

    action_codename = 'discordpostmessage'
    app_name = 'discordintegration'
    action_type = "DiscordPostMessage"

    class Meta:
        permissions = (
            ('can_execute_discordpostmessage', 'Can execute discord post message'),
        )

    def revert(self):
        super().revert({}, f"channels/{self.channel_id}/messages/{self.message_id}", method='DELETE')

    def execute(self):
        # Execute action if it didn't originate in the community OR it was previously reverted
        if not self.community_origin or (self.community_origin and self.community_revert):
            message = self.community.make_call(f"channels/{self.channel_id}/messages", {'content': self.text})

            self.message_id = message['id']
            self.community_post = self.message_id
            self.save()

class DiscordDeleteMessage(PlatformAction):
    channel_id = models.IntegerField()
    message_id = models.IntegerField()
    text = models.TextField(blank=True, default='')

    ACTION = f"channels/{channel_id}/messages/{message_id}"
    AUTH = 'user'

    action_codename = 'discorddeletemessage'
    app_name = 'discordintegration'
    action_type = "DiscordDeleteMessage"

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
    channel_id = models.IntegerField()
    name = models.TextField()
    name_old = models.TextField(blank=True, default='')

    ACTION = f"channels/{channel_id}"
    AUTH = 'user'

    action_codename = 'discordrenamechannel'
    app_name = 'discordintegration'
    action_type = "DiscordRenameChannel"

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
    guild_id = models.IntegerField()
    channel_id = models.IntegerField(blank=True)
    name = models.TextField()

    ACTION = f"guilds/{guild_id}/channels"
    AUTH = 'user'

    action_codename = 'discordcreatechannel'
    app_name = 'discordintegration'
    action_type = "DiscordCreateChannel"

    class Meta:
        permissions = (
            ('can_execute_discordcreatechannel', 'Can execute discord create channel'),
        )

    def revert(self):
        super().revert({}, f"channels/{self.channel_id}", method='DELETE')

    def execute(self):
        # Execute action if it didn't originate in the community OR it was previously reverted
        if not self.community_origin or (self.community_origin and self.community_revert):
            channel = self.community.make_call(f"guilds/{self.guild_id}/channels", {'name': self.name})
            self.channel_id = channel['id']

            # Create a new DiscordChannel object
            DiscordChannel.objects.get_or_create(
                guild_id=self.guild_id,
                channel_id=self.channel_id,
                channel_name=channel['name']
            )

class DiscordDeleteChannel(PlatformAction):
    channel_id = models.IntegerField()

    ACTION = f"channels/{channel_id}"
    AUTH = 'user'

    action_codename = 'discorddeletechannel'
    app_name = 'discordintegration'
    action_type = "DiscordDeleteChannel"

    class Meta:
        permissions = (
            ('can_execute_discorddeletechannel', 'Can execute discord delete channel'),
        )

    def execute(self):
        # Execute action if it didn't originate in the community
        if not self.community_origin:
            self.community.make_call(f"channels/{self.channel_id}", method='DELETE')
