from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from slackintegration.models import SlackUser, SlackIntegration
from urllib import parse
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

class SlackBackend(BaseBackend):

    def authenticate(self, request, oauth=None):
        
        logging.debug(access_token)
        
        if not oauth:
            return None
        
        s = SlackIntegration.objects.filter(team_id=oauth['team_id'])
        if s.exists():
#             user_data = parse.urlencode({
#                     'token': oauth['access_token']
#                     }).encode()
#                 
#             user_req = urllib.request.Request('https://slack.com/api/users.identity?', data=user_data)
#             user_resp = urllib.request.urlopen(user_req)
#             user_res = json.loads(user_resp.read().decode('utf-8'))
                
            
            slack_user = SlackUser.objects.filter(user_id=oauth['user']['id'])
            if slack_user.exists():
                # update user info
                slack_user[0].user_id = oauth['user']['id']
                slack_user[0].user_name = oauth['user']['name']
                slack_user[0].avatar = oauth['user']['image_24']
                slack_user[0].access_token = oauth['access_token']
                slack_user[0].save()
                
                dju = slack_user[0].django_user
                dju.username = oauth['user']['id']
                dju.password = oauth['access_token']
                dju.save()
            else:
                dju,_ = User.objects.get_or_create(username=oauth['access_token']['user']['id'],
                                                     password=oauth['access_token'])
                
                slack_user = SlackUser.objects.create(
                    django_user = dju,
                    slack_team = s,
                    user_id = oauth['user']['id'],
                    user_name = oauth['user']['name'],
                    avatar = oauth['user']['image_24'],
                    access_token = oauth['access_token'],
                    )
            return dju
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None