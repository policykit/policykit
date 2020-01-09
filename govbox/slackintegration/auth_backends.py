from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from django.contrib.auth.models import User
from slackintegration.models import SlackUser, SlackIntegration
from urllib import parse
import urllib.request
import json

class SlackBackend(BaseBackend):

    def authenticate(self, request, access_token=None, team_id=None):
        if not team_id or not access_token:
            return None
        
        s = SlackIntegration.objects.filter(team_id=team_id)
        if s.exists():
            user_data = parse.urlencode({
                    'token': access_token
                    }).encode()
                
            user_req = urllib.request.Request('https://slack.com/api/users.identity?', data=user_data)
            user_resp = urllib.request.urlopen(user_req)
            user_res = json.loads(user_resp.read().decode('utf-8'))
                
            
            slack_user = SlackUser.objects.filter(user_id=user_res['user']['id'])
            if slack_user.exists():
                # update user info
                slack_user[0].user_id = user_res['user']['id']
                slack_user[0].user_name = user_res['user']['name']
                slack_user[0].avatar = user_res['user']['image_24']
                slack_user[0].access_token = access_token
                slack_user[0].save()
                
                dju = slack_user[0].django_user
                dju.username = user_res['user']['id']
                dju.password = access_token
                dju.save()
            else:
                dju,_ = User.objects.get_or_create(username=user_res['user']['id'],
                                                     password=access_token)
                
                slack_user = SlackUser.objects.create(
                    django_user = dju,
                    slack_team = s,
                    user_id = user_res['user']['id'],
                    user_name = user_res['user']['name'],
                    avatar = user_res['user']['image_24'],
                    access_token = access_token,
                    )
            return dju
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None