from django.db import models
from govrules.models import CommunityIntegration

# Create your models here.


class SlackIntegration(CommunityIntegration):
    API = 'https://slack.com/api/'
    
    team_name = models.CharField('team_name', 
                                  max_length=1000)
    team_id = models.CharField('team_id', max_length=150, unique=True)

    access_token = models.CharField('access_token', 
                                    max_length=300, 
                                    unique=True)
    


class UserSignIn(models.Model):
    slack_team = models.ForeignKey(
        SlackIntegration,
        models.CASCADE,
    )
    
    access_token = models.CharField('access_token', 
                                    max_length=300, 
                                    unique=True)

    
    
    
class SlackUserGroup(models.Model):
    API_METHOD = 'usergroups.create'
    name = models.CharField('name', max_length=150, unique=True)
    description = models.TextField()
    
