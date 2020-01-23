from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from slackintegration.models import SlackUser, SlackIntegration
from urllib import parse
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

class SlackBackend(BaseBackend):

    def authenticate(self, request, oauth=None):
        if not oauth:
            return None

        logger.info(oauth)
        
        s = SlackIntegration.objects.filter(team_id=oauth['team']['id'])

        if s.exists():
            user_data = parse.urlencode({
                    'token': oauth['authed_user']['access_token']
                    }).encode()

                
            
            slack_user = SlackUser.objects.filter(user_id=oauth['authed_user']['id'])
            if slack_user.exists():
                # update user info
                slack_user = slack_user[0]
                slack_user.user_id = oauth['authed_user']['id']
                slack_user.access_token = oauth['authed_user']['access_token']
                slack_user.community_integration = s[0]
                
                slack_user.username = oauth['authed_user']['id']
                slack_user.password = oauth['authed_user']['access_token']
                slack_user.save()

            else:
                
                                 
                user_req = urllib.request.Request('https://slack.com/api/users.identity?', data=user_data)
                user_resp = urllib.request.urlopen(user_req)
                user_res = json.loads(user_resp.read().decode('utf-8'))

                slack_user = SlackUser.objects.create(
                    username=oauth['authed_user']['id'],
                    password=oauth['authed_user']['access_token'],
                    community_integration = s[0],
                    user_id = oauth['authed_user']['id'],
                    readable_name = user_res['user']['name'],
                    avatar = user_res['user']['image_24'],
                    access_token = oauth['authed_user']['access_token'],
                    )
            return slack_user
        return None


    def get_user(self, user_id):
        try:
            return SlackUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None