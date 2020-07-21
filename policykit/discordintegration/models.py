from django.db import models
from policyengine.models import Community, CommunityUser, CommunityAction
from django.contrib.auth.models import Permission, ContentType, User
from django.utils.functional import lazy
from policykit.settings import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_BOT_TOKEN
import urllib
from urllib import parse
import base64
import json
import logging

logger = logging.getLogger(__name__)

DISCORD_ACTIONS = ['discordpostmessage']

# Create your models here.


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

    team_id = models.CharField('team_id', max_length=150, unique=True)
    access_token = models.CharField('access_token', max_length=300, unique=True)
    refresh_token = models.CharField('refresh_token', max_length=500, null=True)

    def refresh_access_token(self):
        res = refresh_access_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()

    def notify_action(self, action, policy, users=None, template=None, channel=None):
        from discordintegration.views import post_policy
        post_policy(policy, action, users, template, channel)

    def save(self, *args, **kwargs):
        super(DiscordCommunity, self).save(*args, **kwargs)

        content_types = ContentType.objects.filter(model__in=DISCORD_ACTIONS)
        perms = Permission.objects.filter(content_type__in=content_types, name__contains="can add ")
        for p in perms:
            self.base_role.permissions.add(p)

    def make_call(self, url, values=None, action=None):
        logger.info(self.API + url)

        if values:
            data = urllib.parse.urlencode(values)
            data = data.encode('utf-8')
            logger.info(data)
        else:
            data = None

        try:
            user_token = False
            req = urllib.request.Request(self.API + url, data)

            if action and action.AUTH == 'user':
                user = action.initiator
                if user.access_token:
                    req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
                    user_token = True
                else:
                    req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
            else:
                req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)

            logger.info(req.headers)
            resp = urllib.request.urlopen(req)
            res = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.reason == 'Unauthorized':
                if user_token:
                    duser = user.discorduser
                    duser.refresh_access_token()
                else:
                    self.refresh_access_token()

                req = urllib.request.Request(self.API + url, data)
                if action and action.AUTH == 'user':
                    user = action.initiator
                    req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
                else:
                    req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
                resp = urllib.request.urlopen(req)
                res = json.loads(resp.read().decode('utf-8'))
            else:
                logger.info(e)
        return res

    def execute_community_action(self, action, delete_policykit_post=True):
        from policyengine.models import LogAPICall, CommunityUser
        from policyengine.views import clean_up_proposals

        logger.info('here')
        obj = action

        if not obj.community_origin or (obj.community_origin and obj.community_revert):
            logger.info('EXECUTING ACTION BELOW:')
            call = self.API + obj.ACTION
            logger.info(call)

            obj_fields = []
            for f in obj._meta.get_fields():
                if f.name not in ['polymorphic_ctype',
                                  'community',
                                  'initiator',
                                  'communityapi_ptr',
                                  'communityaction',
                                  'communityactionbundle',
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
                    bundle = action.communityactionbundle_set.all()
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
    avatar = models.CharField('avatar', max_length=500, null=True)

    def refresh_access_token(self):
        res = refresh_access_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()

    def save(self, *args, **kwargs):
        super(DiscordUser, self).save(*args, **kwargs)
        group = self.community.base_role
        group.user_set.add(self)

class DiscordPostMessage(CommunityAction):

    def get_choices(self):
        req = urllib.request.Request('https://discordapp.com/api/guilds/%s/channels' % self.community.team_id)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
        req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
        resp = urllib.request.urlopen(req)
        channels = json.loads(resp.read().decode('utf-8'))

        channelTuples = []
        for c in channels:
            channelTuples.append((c['id'], c['name']))
        return channelTuples

    choices = get_choices(self)

    text = models.TextField()
    channel = models.CharField(max_length=18, choices=choices)

    ACTION = 'channels/{0}/messages'.format(channel)
    AUTH = 'user'

    action_codename = 'discordpostmessage'

    class Meta:
        permissions = (
            ('can_execute_discordpostmessage', 'Can execute discord post message'),
        )

    def revert(self):
        values = {}
        super.revert(values, 'channels/{0}/messages/{1}'.format(self.channel, self.id))

    def execute(self):
        if not self.community_revert:
            res = self.community.make_call('channels/%s/messages' % channel)
            self.id = res['id']
        super().execute()
