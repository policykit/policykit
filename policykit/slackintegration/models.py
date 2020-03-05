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
            self.user_group.permissions.add(p)
            

class SlackUser(CommunityUser):
    
    user_id = models.CharField('user_id', 
                                max_length=300)

    avatar = models.CharField('avatar', 
                               max_length=500, 
                               null=True)
    
    def save(self, *args, **kwargs):      
        super(SlackUser, self).save(*args, **kwargs)
        group = self.community_integration.user_group
        group.user_set.add(self)

    
class SlackPostMessage(CommunityAPI):
    ACTION = 'chat.postMessage'
    AUTH = 'admin_bot'
    text = models.TextField()
    channel = models.CharField('channel', max_length=150)
    
    def revert(self):
        admin_user = SlackUser.objects.filter(is_community_admin=True)[0]
        values = {'token': admin_user.access_token,
                  'ts': self.time_stamp,
                  'channel': self.channel
                }
        super().revert(values, SlackIntegration.API + 'chat.delete')
    
    def post_policy(self):
        values = {'channel': self.channel,
                  'token': self.community_integration.access_token
                  }
        super().post_policy(values, SlackIntegration.API + 'chat.postMessage')
            
    
class SlackScheduleMessage(CommunityAPI):
    ACTION = 'chat.scheduleMessage'
    text = models.TextField()
    channel = models.CharField('channel', max_length=150)
    post_at = models.IntegerField('post at')

class SlackRenameConversation(CommunityAPI):
    ACTION = 'conversations.rename'
    AUTH = 'admin_user'
    name = models.CharField('name', max_length=150)
    channel = models.CharField('channel', max_length=150)
    
    def get_channel_info(self):
        values = {'token': self.community_integration.access_token,
                'channel': self.channel
                }
        data = urllib.parse.urlencode(values)
        data = data.encode('utf-8')
        req = urllib.request.Request('https://slack.com/api/conversations.info?', data)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        logger.info(res)
        prev_names = res['channel']['previous_names']
        return prev_names
        
    def revert(self):
        values = {'name': self.prev_name,
                'token': self.initiator.access_token,
                'channel': self.channel
                }
        super().revert(values, SlackIntegration.API + 'conversations.rename')
    
    def post_policy(self):
        values = {'channel': self.channel,
                  'token': self.community_integration.access_token
                  }
        super().post_policy(values, SlackIntegration.API + 'chat.postMessage')
        
                    
        
class SlackKickConversation(CommunityAPI):
    ACTION = 'conversations.kick'
    AUTH = 'user'
    user = models.CharField('user', max_length=15)
    channel = models.CharField('channel', max_length=150)


class SlackJoinConversation(CommunityAPI):
    ACTION = 'conversations.invite'
    channel = models.CharField('channel', max_length=150)
    users = models.CharField('users', max_length=15)
        
    def revert(self):
        if self.inviter != 'UTE9MFJJ0':
            values = {'user': self.users,
                      'token': self.initiator.access_token,
                      'channel': self.channel
                    }
            super().revert(values, SlackIntegration.API + 'conversations.kick')
    
    def post_policy(self):
        values = {'channel': self.channel,
                  'token': self.community_integration.access_token
                  }
        super().post_policy(values, SlackIntegration.API + 'chat.postMessage')


class SlackPinMessage(CommunityAPI):
    ACTION = 'pins.add'
    channel = models.CharField('channel', max_length=150)
    timestamp = models.CharField('timestamp', max_length=150)

    def revert(self):
        values = {'token': self.community_integration.access_token,
                  'channel': self.channel,
                  'timestamp': self.timestamp
                }
        super().revert(values, SlackIntegration.API + 'pins.remove')

    def post_policy(self):
        values = {'channel': self.channel,
                  'token': self.community_integration.access_token
                  }
        super().post_policy(values, SlackIntegration.API + 'chat.postMessage')
    
    def save(self, user=None, *args, **kwargs):
        if self.timestamp and user != 'UTE9MFJJ0':
            self.revert()
            self.post_policy()
            super(SlackPinMessage, self).save(*args, **kwargs)
        if not user:
            super(SlackPinMessage, self).save(*args, **kwargs)
            
        
        
            
    
