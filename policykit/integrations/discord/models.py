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

DISCORD_VIEW_PERMS = [
    'Can view discord post message',
    'Can view discord delete message',
    'Can view discord rename channel',
    'Can view discord create channel',
    'Can view discord delete channel'
]
DISCORD_PROPOSE_PERMS = [
    'Can add discord post message',
    'Can add discord delete message',
    'Can add discord rename channel',
    'Can add discord create channel',
    'Can add discord delete channel'
]
DISCORD_EXECUTE_PERMS = [
    'Can execute discord post message',
    'Can execute discord delete message',
    'Can execute discord rename channel',
    'Can execute discord create channel',
    'Can execute discord delete channel'
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

class DiscordStarterKit(StarterKit):
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
                c.name = "Discord: " + community.community_name + ": " + role.role_name
                c.description = role.description
                c.save()

            for perm in role.permissions.all():
                c.permissions.add(perm)

            jsonDec = json.decoder.JSONDecoder()
            perm_set = jsonDec.decode(role.plat_perm_set)

            if 'view' in perm_set:
                for perm in DISCORD_VIEW_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)
            if 'propose' in perm_set:
                for perm in DISCORD_PROPOSE_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)
            if 'execute' in perm_set:
                for perm in DISCORD_EXECUTE_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)

            if role.user_group == "admins":
                group = CommunityUser.objects.filter(community = community, is_community_admin = True)
                for user in group:
                    c.user_set.add(user)
            elif role.user_group == "nonadmins":
                group = CommunityUser.objects.filter(community = community, is_community_admin = False)
                for user in group:
                    c.user_set.add(user)
            elif role.user_group == "all":
                group = CommunityUser.objects.filter(community = community)
                for user in group:
                    c.user_set.add(user)
            elif role.user_group == "creator":
                user = CommunityUser.objects.get(access_token=creator_token)
                c.user_set.add(user)

            c.save()
