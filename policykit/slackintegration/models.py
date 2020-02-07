from django.db import models
from policyengine.models import CommunityIntegration, CommunityUser, CommunityAction, Policy, RulePolicy
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


    
class SlackPostMessage(CommunityAction):
    ACTION = 'chat.postMessage'
    text = models.TextField()
    channel = models.CharField('channel', max_length=150)
    
    def revert(self, time_stamp):
        values = {'token': self.author.access_token,
                  'ts': time_stamp,
                  'channel': self.channel
                }
        super().revert(values, SlackIntegration.API + 'chat.delete')
    
    def post_rule(self):
        values = {'channel': self.channel,
                  'token': self.community_integration.access_token
                  }
        super().post_rule(values, SlackIntegration.API + 'chat.postMessage')
        
    
    def save(self, time_stamp=None, poster=None, *args, **kwargs): 
        if time_stamp and poster != 'UTE9MFJJ0':
            self.revert(time_stamp)
            self.post_rule()
            super(SlackPostMessage, self).save(*args, **kwargs)
            
    
class SlackScheduleMessage(CommunityAction):
    ACTION = 'chat.scheduleMessage'
    text = models.TextField()
    channel = models.CharField('channel', max_length=150)
    post_at = models.IntegerField('post at')

class SlackRenameConversation(CommunityAction):
    ACTION = 'conversations.rename'
    AUTH = 'user'
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
        
    def revert(self, prev_name):
        values = {'name': prev_name,
                'token': self.author.access_token,
                'channel': self.channel
                }
        super().revert(values, SlackIntegration.API + 'conversations.rename')
    
    def post_rule(self):
        values = {'channel': self.channel,
                  'token': self.community_integration.access_token
                  }
        super().post_rule(values, SlackIntegration.API + 'chat.postMessage')
        
        
    def save(self, slack_revert=False, *args, **kwargs):
        if slack_revert:
            prev_names = self.get_channel_info()
            if len(prev_names) == 1:
                self.revert(prev_names[0])
                self.post_rule()
                super(SlackRenameConversation, self).save(*args, **kwargs)
            
            if len(prev_names) > 1:
                former_name = prev_names[1]
                if former_name != self.name:
                    self.revert(prev_names[0])
                    self.post_rule()
                    super(SlackRenameConversation, self).save(*args, **kwargs)
                    
        
class SlackKickConversation(CommunityAction):
    ACTION = 'conversations.kick'
    AUTH = 'user'
    user = models.CharField('user', max_length=15)
    channel = models.CharField('channel', max_length=150)


class SlackJoinConversation(CommunityAction):
    ACTION = 'conversations.invite'
    channel = models.CharField('channel', max_length=150)
    users = models.CharField('users', max_length=15)
        
    def revert(self):
        values = {'user': self.users,
                  'token': self.author.access_token,
                  'channel': self.channel
                }
        super().revert(values, SlackIntegration.API + 'conversations.kick')
    
    def post_rule(self):
        values = {'channel': self.channel,
                  'token': self.community_integration.access_token
                  }
        super().post_rule(values, SlackIntegration.API + 'chat.postMessage')
    
    def save(self, slack_revert=False, inviter=None, *args, **kwargs):
        if slack_revert and inviter != 'UTE9MFJJ0':
            self.revert()
            self.post_rule()
            super(SlackJoinConversation, self).save(*args, **kwargs)


class SlackPinMessage(CommunityAction):
    ACTION = 'pins.add'
    text = models.TextField()
    channel = models.CharField('channel', max_length=150)

    def post_rule(self):
        values = {'channel': self.channel,
                  'token': self.community_integration.access_token
                  }
        super().post_rule(values, SlackIntegration.API + 'pins.add')
        
    
    def save(self, *args, **kwargs): 
        self.post_rule()
        super(SlackPostMessage, self).save(*args, **kwargs)
            
        
        
            
    
