from django.db import models
from govrules.models import CommunityIntegration, CommunityUser, CommunityAction, CommunityObject
from django.contrib.auth.models import Permission, ContentType, User
import urllib
import json
import logging

logger = logging.getLogger(__name__)

SLACK_ACTIONS = ['slackpostmessage', 
                 'slackschedulemessage', 
                 'slackrenameconversation',
                 'slackkickconversation'
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
        data = {'token': self.community_integration.access_token,
                'channel': self.channel
                }
        req = urllib.request.Request('https://slack.com/api/conversations.info?', data=data)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        logger.info(res)
        prev_name = res['channel']['previous_names'][-1]
        return prev_name
        
    def revert(self, prev_name):
        data = {'name': prev_name,
                'token': self.author.access_token,
                'channel': self.channel
                }
        req = urllib.request.Request('https://slack.com/api/conversations.rename?', data=data)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        logger.info(res)
    
    def save(self, *args, **kwargs):
        revert = kwargs.get('slack_revert')
        if revert:
            prev_name = self.get_channel_info()
            self.revert(prev_name)
        
        super(SlackRenameConversation, self).save(*args, **kwargs)
        
    
class SlackKickConversation(CommunityAction):
    ACTION = 'conversations.kick'
    AUTH = 'user'
    user = models.CharField('user', max_length=15)
    channel = models.CharField('channel', max_length=150)

