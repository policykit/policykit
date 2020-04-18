from django.db import models
from policyengine.models import Community, CommunityUser, CommunityAction
from django.contrib.auth.models import Permission, ContentType, User
from policykit.settings import REDDIT_CLIENT_SECRET
import urllib
from urllib import parse
import base64
import json

# Create your models here.


def refresh_token(refresh_token):
    data = parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
        }).encode()
        
    req = urllib.request.Request('https://www.reddit.com/api/v1/access_token', data=data)
    
    credentials = ('%s:%s' % ('QrZzzkLgVc1x6w', REDDIT_CLIENT_SECRET))
    encoded_credentials = base64.b64encode(credentials.encode('ascii'))

    req.add_header("Authorization", "Basic %s" % encoded_credentials.decode("ascii"))
    req.add_header("User-Agent", "PolicyKit-App-Reddit-Integration v 1.0")

    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))
    return res


class RedditCommunity(Community):
    API = 'https://reddit.com/api/v1/'
    
    team_id = models.CharField('team_id', max_length=150, unique=True)

    access_token = models.CharField('access_token', 
                                    max_length=300, 
                                    unique=True)
    
    refresh_token = models.CharField('refresh_token', 
                               max_length=500, 
                               null=True)
    
    
    def refresh_token(self):
        res = refresh_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()

    
    def notify_action(self, action, policy, users, post_type='channel', template=None, channel=None):
        from redditintegration.views import post_policy
        post_policy(policy, action, users, post_type, template, channel)
    
    def save(self, *args, **kwargs):      
        super(RedditCommunity, self).save(*args, **kwargs)
        
#         content_types = ContentType.objects.filter(model__in=REDDIT_ACTIONS)
#         perms = Permission.objects.filter(content_type__in=content_types, name__contains="can add ")
#         for p in perms:
#             self.base_role.permissions.add(p)
            

class RedditUser(CommunityUser):
    refresh_token = models.CharField('refresh_token', 
                               max_length=500, 
                               null=True)
    
    def refresh_token(self):
        res = refresh_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()
    
    def save(self, *args, **kwargs):      
        super(RedditUser, self).save(*args, **kwargs)
        group = self.community.base_role
        group.user_set.add(self)



