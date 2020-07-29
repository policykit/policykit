from django.db import models
from policyengine.models import Community, CommunityUser, PlatformAction
from django.contrib.auth.models import Permission, ContentType, User
import urllib
import json
import logging

logger = logging.getLogger(__name__)

SLACK_ACTIONS = ['slackpostmessage',
                 'slackschedulemessage',
                 'slackrenameconversation',
                 'slackkickconversation',
                 'slackjoinconversation',
                 'slackpinmessage'
                 ]

class SlackCommunity(Community):
    API = 'https://slack.com/api/'

    team_id = models.CharField('team_id', max_length=150, unique=True)

    access_token = models.CharField('access_token',
                                    max_length=300,
                                    unique=True)

    bot_id = models.CharField('bot_id', max_length=150, unique=True, default='')

    def notify_action(self, action, policy, users, post_type='channel', template=None, channel=None):
        from slackintegration.views import post_policy
        post_policy(policy, action, users, post_type, template, channel)

    def make_call(self, url, values=None):
        logger.info(url)
        if values:
            data = urllib.parse.urlencode(values)
            data = data.encode('utf-8')
            logger.info(data)
        else:
            data = None

        call_info = SlackCommunity.API + url + '?'
        req = urllib.request.Request(call_info, data)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        return res

    def save(self, *args, **kwargs):
        super(SlackCommunity, self).save(*args, **kwargs)

        content_types = ContentType.objects.filter(model__in=SLACK_ACTIONS)
        perms = Permission.objects.filter(content_type__in=content_types, name__contains="can add ")
        for p in perms:
            self.base_role.permissions.add(p)
                        
    def execute_platform_action(self, action, delete_policykit_post=True):

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
                                  'platformaction',
                                  'platformactionbundle',
                                  'community_revert',
                                  'community_origin',
                                  'is_bundled'
                                  ]:
                    obj_fields.append(f.name)

            data = {}

            if obj.AUTH == "user":
                data['token'] = action.proposal.author.access_token
                if not data['token']:
                    admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
                    data['token'] = admin_user.access_token
            elif obj.AUTH == "admin_bot":
                if action.proposal.author.is_community_admin:
                    data['token'] = action.proposal.author.access_token
                else:
                    data['token'] = self.access_token
            elif obj.AUTH == "admin_user":
                admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
                data['token'] = admin_user.access_token
            else:
                data['token'] = self.access_token


            for item in obj_fields:
                try :
                    if item != 'id':
                        value = getattr(obj, item)
                        data[item] = value
                except obj.DoesNotExist:
                    continue

            res = LogAPICall.make_api_call(self, data, call)


            # delete PolicyKit Post
            if delete_policykit_post:
                posted_action = None
                if action.is_bundled:
                    bundle = action.platformactionbundle_set.all()
                    if bundle.exists():
                        posted_action = bundle[0]
                else:
                    posted_action = action

                if posted_action.community_post:
                    admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
                    values = {'token': admin_user.access_token,
                              'ts': posted_action.community_post,
                              'channel': obj.channel
                            }
                    call = self.API + 'chat.delete'
                    _ = LogAPICall.make_api_call(self, values, call)

            if res['ok']:
                clean_up_proposals(action, True)
            else:
                error_message = res['error']
                logger.info(error_message)
                clean_up_proposals(action, False)

        else:
            clean_up_proposals(action, True)


class SlackUser(CommunityUser):
    avatar = models.CharField('avatar',
                               max_length=500,
                               null=True)

    def save(self, *args, **kwargs):
        super(SlackUser, self).save(*args, **kwargs)
        group = self.community.base_role
        group.user_set.add(self)

    
class SlackPostMessage(PlatformAction):
    ACTION = 'chat.postMessage'
    AUTH = 'admin_bot'
    text = models.TextField()
    channel = models.CharField('channel', max_length=150)

    action_codename = 'slackpostmessage'
    app_name = 'slackintegration'
    
    class Meta:
        permissions = (
            ('can_execute_slackpostmessage', 'Can execute slack post message'),
        )

    def revert(self):
        admin_user = SlackUser.objects.filter(is_community_admin=True)[0]
        values = {'token': admin_user.access_token,
                  'ts': self.time_stamp,
                  'channel': self.channel
                }
        super().revert(values, 'chat.delete')
    
class SlackRenameConversation(PlatformAction):
    ACTION = 'conversations.rename'
    AUTH = 'admin_user'

    action_type = "SlackRenameConversation"

    name = models.CharField('name', max_length=150)
    channel = models.CharField('channel', max_length=150)

    action_codename = 'slackrenameconversation'
    app_name = 'slackintegration'
    
    class Meta:
        permissions = (
            ('can_execute_slackrenameconversation', 'Can execute slack rename conversation'),
        )

    def get_channel_info(self):
        values = {'token': self.community.access_token,
                'channel': self.channel
                }
        data = urllib.parse.urlencode(values)
        data = data.encode('utf-8')
        req = urllib.request.Request('https://slack.com/api/conversations.info?', data)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        prev_names = res['channel']['previous_names']
        return prev_names

    def revert(self):
        values = {'name': self.prev_name,
                'token': self.initiator.access_token,
                'channel': self.channel
                }
        super().revert(values, 'conversations.rename')
        
class SlackJoinConversation(PlatformAction):
    ACTION = 'conversations.invite'
    AUTH = 'admin_user'
    channel = models.CharField('channel', max_length=150)
    users = models.CharField('users', max_length=15)

    action_codename = 'slackjoinconversation'
    app_name = 'slackintegration'
    
    class Meta:
        permissions = (
            ('can_execute_slackjoinconversation', 'Can execute slack join conversation'),
        )

    def revert(self):
        admin_user = SlackUser.objects.filter(is_community_admin=True)[0]
        values = {'user': self.users,
                  'token': admin_user.access_token,
                  'channel': self.channel
                }
        super().revert(values, 'conversations.kick')

class SlackPinMessage(PlatformAction):
    ACTION = 'pins.add'
    AUTH = 'bot'
    channel = models.CharField('channel', max_length=150)
    timestamp = models.CharField('timestamp', max_length=150)

    action_codename = 'slackpinmessage'
    app_name = 'slackintegration'

    class Meta:
        permissions = (
            ('can_execute_slackpinmessage', 'Can execute slack pin message'),
        )

    def revert(self):
        values = {'token': self.community.access_token,
                  'channel': self.channel,
                  'timestamp': self.timestamp
                }
        super().revert(values, 'pins.remove')

class SlackScheduleMessage(PlatformAction):
    ACTION = 'chat.scheduleMessage'
    text = models.TextField()
    channel = models.CharField('channel', max_length=150)
    post_at = models.IntegerField('post at')

    action_codename = 'slackschedulemessage'
    app_name = 'slackintegration'
    
    class Meta:
        permissions = (
            ('can_execute_slackschedulemessage', 'Can execute slack schedule message'),
        )

class SlackKickConversation(PlatformAction):
    ACTION = 'conversations.kick'
    AUTH = 'user'
    user = models.CharField('user', max_length=15)
    channel = models.CharField('channel', max_length=150)

    action_codename = 'slackkickconversation'
    app_name = 'slackintegration'
    
    class Meta:
        permissions = (
            ('can_execute_slackkickconversation', 'Can execute slack kick conversation'),
        )
