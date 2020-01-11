from django.db import models
from govrules.models import CommunityIntegration
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission

# Create your models here.


class SlackIntegration(CommunityIntegration):
    API = 'https://slack.com/api/'
    
    team_name = models.CharField('team_name', 
                                  max_length=1000)
    team_id = models.CharField('team_id', max_length=150, unique=True)

    access_token = models.CharField('access_token', 
                                    max_length=300, 
                                    unique=True)
    


class SlackUser(models.Model):
    
    django_user = models.ForeignKey(User,
                                    models.CASCADE)
    
    slack_team = models.ForeignKey(
        SlackIntegration,
        models.CASCADE,
    )
    
    user_name = models.CharField('user_name', 
                                  max_length=300)
    
    user_id = models.CharField('user_id', 
                                max_length=300)
    
    access_token = models.CharField('access_token', 
                                     max_length=300, 
                                     unique=True)
    
    avatar = models.CharField('avatar', 
                               max_length=500, 
                               null=True)

    
    def save(self, *args, **kwargs):
        permission = Permission.objects.get(name='Can add proposal')
        self.django_user.user_permissions.add(permission)
        
        super(SlackUser, self).save(*args, **kwargs)
        
        
    
    
class SlackUserGroup(models.Model):
    API_METHOD = 'usergroups.create'
    name = models.CharField('name', max_length=150, unique=True)
    description = models.TextField()
    
