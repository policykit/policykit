from django.db import models
from govrules.models import CommunityIntegration, CommunityUser
from django.contrib.auth.models import Permission, ContentType, User


class SlackIntegration(CommunityIntegration):
    API = 'https://slack.com/api/'
    
    team_id = models.CharField('team_id', max_length=150, unique=True)

    access_token = models.CharField('access_token', 
                                    max_length=300, 
                                    unique=True)
    
    def save(self, *args, **kwargs):      
        super(SlackIntegration, self).save(*args, **kwargs)
        
        content_type = ContentType.objects.get(model='slackchat')
        perms = Permission.objects.filter(content_type=content_type)
        for p in perms:
            self.user_group.permissions.add(p)
    


class SlackUser(CommunityUser):
    
    user_id = models.CharField('user_id', 
                                max_length=300)
    
    access_token = models.CharField('access_token', 
                                     max_length=300, 
                                     unique=True)
    
    avatar = models.CharField('avatar', 
                               max_length=500, 
                               null=True)
    
    def save(self, *args, **kwargs):      
        super(SlackUser, self).save(*args, **kwargs)
        group = self.community_integration.user_group
        group.user_set.add(self)



class SlackChat(models.Model):
    
    POST = 'chat.postMessage'
    message = models.TextField()


class SlackConversation(models.Model):
    
    CREATE = 'conversations.create'
    RENAME = 'conversations.rename'
    
    name = models.CharField('name', max_length=150, unique=True)
    
    
    
class SlackUserGroup(models.Model):
    API_METHOD = 'usergroups.create'
    name = models.CharField('name', max_length=150, unique=True)
    description = models.TextField()
    
    
