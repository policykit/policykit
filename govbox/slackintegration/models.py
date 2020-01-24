from django.db import models
from govrules.models import CommunityIntegration, CommunityUser, CommunityAction
from django.contrib.auth.models import Permission, ContentType, User


SLACK_ACTIONS = ['slackpostmessage', 
                 'slackschedulemessage', 
                 'slackrenameconversation']

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
    name = models.CharField('name', max_length=150, unique=True)
    channel = models.CharField('channel', max_length=150)

    
