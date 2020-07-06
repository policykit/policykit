from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from slackintegration.models import SlackUser, SlackCommunity
from urllib import parse
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

class SlackBackend(BaseBackend):

    def authenticate(self, request, oauth=None, platform=None):
        if not oauth:
            return None
        
        if platform != 'slack':
            return None

        s = SlackCommunity.objects.filter(team_id=oauth['team']['id'])

        if s.exists():
            user_data = parse.urlencode({
                    'token': oauth['authed_user']['access_token']
                    }).encode()

            slack_user = SlackUser.objects.filter(username=oauth['authed_user']['id'])
            

            if slack_user.exists() and slack_user[0].readable_name != None:
                # update user info
                slack_user = slack_user[0]
                slack_user.access_token = oauth['authed_user']['access_token']
                slack_user.community = s[0]
                slack_user.password = oauth['authed_user']['access_token']
                slack_user.save()
                
            else:
                user_req = urllib.request.Request('https://slack.com/api/users.identity?', data=user_data)
                user_resp = urllib.request.urlopen(user_req)
                user_res = json.loads(user_resp.read().decode('utf-8'))


                if slack_user.exists():
                    slack_user = slack_user[0]
                    slack_user.access_token = oauth['authed_user']['access_token']
                    slack_user.community = s[0]
                    slack_user.password = oauth['authed_user']['access_token']
                    slack_user.readable_name = user_res['user']['name']
                    slack_user.avatar = user_res['user']['image_24']
                    slack_user.save()
                else:
                    slack_user,_ = SlackUser.objects.get_or_create(
                        username=oauth['authed_user']['id'],
                        password=oauth['authed_user']['access_token'],
                        community = s[0],
                        readable_name = user_res['user']['name'],
                        avatar = user_res['user']['image_24'],
                        access_token = oauth['authed_user']['access_token'],
                        )
            return slack_user
        return None

    def check_app(self, user_id):
        try:

        except:

    def get_user(self, user_id):
        try:
            return SlackUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None