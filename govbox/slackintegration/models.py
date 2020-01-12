from django.db import models
from govrules.models import CommunityIntegration, CommunityUser
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission

# Create your models here.


class SlackIntegration(CommunityIntegration):
    API = 'https://slack.com/api/'
    
    team_id = models.CharField('team_id', max_length=150, unique=True)

    access_token = models.CharField('access_token', 
                                    max_length=300, 
                                    unique=True)
    


class SlackUser(CommunityUser):
    
    user_id = models.CharField('user_id', 
                                max_length=300)
    
    access_token = models.CharField('access_token', 
                                     max_length=300, 
                                     unique=True)
    
    avatar = models.CharField('avatar', 
                               max_length=500, 
                               null=True)


    
    
class SlackUserGroup(models.Model):
    API_METHOD = 'usergroups.create'
    name = models.CharField('name', max_length=150, unique=True)
    description = models.TextField()
    
