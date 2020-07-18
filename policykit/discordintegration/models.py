from django.db import models
from policyengine.models import Community, CommunityUser, CommunityAction
from django.contrib.auth.models import Permission, ContentType, User
from policykit.settings import DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET
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

    req.add_header("Authorization", "Basic %s" % encoded_credentials.decode("ascii"))

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

    def notify_action(self, action, policy, users=None):
        from discordintegration.views import post_policy
        post_policy(policy, action, users)

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
                    req.add_header('Authorization', 'Bearer %s' % user.access_token)
                    user_token = True
                else:
                    req.add_header('Authorization', 'Bearer %s' % self.access_token)
            else:
                req.add_header('Authorization', 'Bearer %s' % self.access_token)

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
                    req.add_header('Authorization', 'Bearer %s' % user.access_token)
                else:
                    req.add_header('Authorization', 'Bearer %s' % self.access_token)
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
            call = obj.ACTION
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
    ACTION = 'chat.postMessage'
    text = models.TextField()
    channel = models.CharField('channel', max_length=150)

    action_codename = 'discordpostmessage'

    class Meta:
        permissions = (
            ('can_execute_discordpostmessage', 'Can execute discord post message'),
        )

    def revert(self):
        values = {
            'channel': self.channel,
            'text': self.text
        }
        super.revert(values, 'chat.delete')
