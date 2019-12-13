from django.db import models
from govrules.models import CommunityIntegration

# Create your models here.


class SlackIntegration(CommunityIntegration):
    API = 'https://slack.com/api/'
    team_id = models.CharField('team_id', max_length=150, unique=True)
    token = models.CharField('token', max_length=300, unique=True)
    
    
class SlackUserGroup(models.Model):
    API_METHOD = 'usergroups.create'
    name = models.CharField('name', max_length=150, unique=True)
    description = models.TextField()
    
