from django.db import models
from policyengine.models import Community, CommunityUser, PlatformAction, StarterKit, ConstitutionPolicy, Proposal, PlatformPolicy, CommunityRole
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
                    'discordrenamechannel'
                  ]

DISCORD_VIEW_PERMS = ['Can view discord post message', 'Can view discord rename channel']

DISCORD_PROPOSE_PERMS = ['Can add discord post message', 'Can add discord rename channel']

DISCORD_EXECUTE_PERMS = ['Can execute discord post message', 'Can execute discord rename channel']

def refresh_access_token(refresh_token):
    data = parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
        }).encode()

    req = urllib.request.Request('https://discordapp.com/api/oauth2/token', data=data)

    credentials = ('%s:%s' % (DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET))
    encoded_credentials = base64.b64encode(credentials.encode('ascii'))

    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("Authorization", "Basic %s" % encoded_credentials.decode("ascii"))
    req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))

    return res

class DiscordCommunity(Community):
    API = 'https://discordapp.com/api/'

    platform = "discord"

    team_id = models.CharField('team_id', max_length=150, unique=True)
    access_token = models.CharField('access_token', max_length=300, unique=True)
    refresh_token = models.CharField('refresh_token', max_length=500, null=True)

    def refresh_access_token(self):
        res = refresh_access_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()

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

    def execute_platform_action(self, action, delete_policykit_post=True):
        from policyengine.models import LogAPICall, CommunityUser
        from policyengine.views import clean_up_proposals

        obj = action

        if not obj.community_origin or (obj.community_origin and obj.community_revert):
            call = self.API + obj.ACTION

            obj_fields = []
            for f in obj._meta.get_fields():
                if f.name not in ['polymorphic_ctype',
                                  'community',
                                  'initiator',
                                  'communityapi_ptr',
                                  'platformaction',
                                  'platformactionbundle',
                                  'community_revert',
                                  'community_origin',
                                  'is_bundled'
                                  ]:
                    obj_fields.append(f.name)

            data = {}

            for item in obj_fields:
                try:
                    if item != 'id':
                        value = getattr(obj, item)
                        data[item] = value
                except obj.DoesNotExist:
                    continue

            res = LogAPICall.make_api_call(self, data, call)

            if delete_policykit_post:
                posted_action = None
                if action.is_bundled:
                    bundle = action.platformactionbundle_set.all()
                    if bundle.exists():
                        posted_action = bundle[0]
                else:
                    posted_action = action

                if posted_action.community_post:
                    data = {}
                    call = 'channels/{0}/messages/{1}'.format(obj.channel, posted_action.community_post)
                    _ = LogAPICall.make_api_call(self, data, call)

            if res['ok']:
                clean_up_proposals(action, True)
            else:
                error_message = res['error']
                logger.info(error_message)
                clean_up_proposals(action, False)
        else:
            clean_up_proposals(action, True)

class DiscordUser(CommunityUser):
    refresh_token = models.CharField('refresh_token', max_length=500, null=True)

    def refresh_access_token(self):
        res = refresh_access_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()

    def save(self, *args, **kwargs):
        super(DiscordUser, self).save(*args, **kwargs)
        group = self.community.base_role
        group.user_set.add(self)

class DiscordPostMessage(PlatformAction):
    guild_id = models.IntegerField()
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
        super().revert({}, "channels/{self.channel_id}/messages/{self.message_id}", method='DELETE')

    def execute(self):
        # Execute action if it didn't originate in the community OR it was previously reverted
        if not self.community_origin or (self.community_origin and self.community_revert):
            message = self.community.make_call(f"channels/{self.channel_id}/messages", {'content': self.text})

            self.message_id = message['id']
            self.community_post = self.message_id
            self.save()

        super().pass_action()

class DiscordRenameChannel(PlatformAction):
    guild_id = models.IntegerField()
    channel_id = models.IntegerField()
    name = models.TextField()

    # Store old name so we can revert the action if necessary
    name_old = models.TextField()

    ACTION = f"channels/{channel_id}"
    AUTH = 'user'

    action_codename = 'discordrenamechannel'
    app_name = 'discordintegration'
    action_type = "DiscordRenameChannel"

    class Meta:
        permissions = (
            ('can_execute_discordrenamechannel', 'Can execute discord rename channel'),
        )

    def execute(self):
        # Execute action if it didn't originate in the community OR it was previously reverted
        if not self.community_origin or (self.community_origin and self.community_revert):
            self.community.make_call(f"channels/{self.channel_id}")
            self.community.make_call(f"channels/{self.channel_id}", {'name': self.name}, method='PATCH')

        super().pass_action()

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
