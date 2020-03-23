from django.db import models
from policyengine.models import CommunityIntegration, CommunityUser, CommunityAPI
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

class SlackIntegration(CommunityIntegration):
    API = 'https://slack.com/api/'
    
    team_id = models.CharField('team_id', max_length=150, unique=True)

    access_token = models.CharField('access_token', 
                                    max_length=300, 
                                    unique=True)
    
    def save(self, *args, **kwargs):      
        super(SlackIntegration, self).save(*args, **kwargs)
        
        content_types = ContentType.objects.filter(model__in=SLACK_ACTIONS)
        perms = Permission.objects.filter(content_type__in=content_types, name__contains="can add ")
        for p in perms:
            self.base_role.permissions.add(p)
            

class SlackUser(CommunityUser):
    avatar = models.CharField('avatar', 
                               max_length=500, 
                               null=True)
    
    def save(self, *args, **kwargs):      
        super(SlackUser, self).save(*args, **kwargs)
        group = self.community_integration.base_role
        group.user_set.add(self)

    
class SlackPostMessage(CommunityAPI):
    ACTION = 'chat.postMessage'
    AUTH = 'admin_bot'
    text = models.TextField()
    channel = models.CharField('channel', max_length=150)
    
    class Meta:
        permissions = (
            ('can_execute', 'Can execute slack post message'),
        )
    
    def revert(self):
        admin_user = SlackUser.objects.filter(is_community_admin=True)[0]
        values = {'token': admin_user.access_token,
                  'ts': self.time_stamp,
                  'channel': self.channel
                }
        super().revert(values, SlackIntegration.API + 'chat.delete')
    
class SlackRenameConversation(CommunityAPI):
    ACTION = 'conversations.rename'
    AUTH = 'admin_user'
    name = models.CharField('name', max_length=150)
    channel = models.CharField('channel', max_length=150)
    
    class Meta:
        permissions = (
            ('can_execute', 'Can execute slack rename conversation'),
        )
    
    def get_channel_info(self):
        values = {'token': self.community_integration.access_token,
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
        super().revert(values, SlackIntegration.API + 'conversations.rename')
        
class SlackJoinConversation(CommunityAPI):
    ACTION = 'conversations.invite'
    AUTH = 'admin_user'
    channel = models.CharField('channel', max_length=150)
    users = models.CharField('users', max_length=15)
    
    class Meta:
        permissions = (
            ('can_execute', 'Can execute slack join conversation'),
        )
        
    def revert(self):
        admin_user = SlackUser.objects.filter(is_community_admin=True)[0]
        values = {'user': self.users,
                  'token': admin_user.access_token,
                  'channel': self.channel
                }
        super().revert(values, SlackIntegration.API + 'conversations.kick')

class SlackPinMessage(CommunityAPI):
    ACTION = 'pins.add'
    AUTH = 'bot'
    channel = models.CharField('channel', max_length=150)
    timestamp = models.CharField('timestamp', max_length=150)

    class Meta:
        permissions = (
            ('can_execute', 'Can execute slack pin message'),
        )

    def revert(self):
        values = {'token': self.community_integration.access_token,
                  'channel': self.channel,
                  'timestamp': self.timestamp
                }
        super().revert(values, SlackIntegration.API + 'pins.remove')

class SlackScheduleMessage(CommunityAPI):
    ACTION = 'chat.scheduleMessage'
    text = models.TextField()
    channel = models.CharField('channel', max_length=150)
    post_at = models.IntegerField('post at')
    
    class Meta:
        permissions = (
            ('can_execute', 'Can execute slack schedule message'),
        )

class SlackKickConversation(CommunityAPI):
    ACTION = 'conversations.kick'
    AUTH = 'user'
    user = models.CharField('user', max_length=15)
    channel = models.CharField('channel', max_length=150)
    
    class Meta:
        permissions = (
            ('can_execute', 'Can execute slack kick conversation'),
        )

