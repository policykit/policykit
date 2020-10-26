from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.slack.models import SlackUser, SlackCommunity
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
            data = parse.urlencode({'token': oauth['authed_user']['access_token']}).encode()
            req = urllib.request.Request('https://slack.com/api/users.identity', data=data)
            resp = urllib.request.urlopen(req)
            user_info = json.loads(resp.read().decode('utf-8'))

            slack_user = SlackUser.objects.filter(username=oauth['authed_user']['id'])

            if slack_user.exists():
                # update user info
                slack_user = slack_user[0]
                slack_user.access_token = oauth['authed_user']['access_token']
                slack_user.community = s[0]
                slack_user.password = oauth['authed_user']['access_token']
                slack_user.readable_name = user_info['user']['name']
                slack_user.avatar = user_info['user']['image_24']
                slack_user.save()
            else:
                slack_user,_ = SlackUser.objects.get_or_create(
                    username = oauth['authed_user']['id'],
                    password = oauth['authed_user']['access_token'],
                    community = s[0],
                    readable_name = user_info['user']['name'],
                    avatar = user_info['user']['image_24'],
                    access_token = oauth['authed_user']['access_token'],
                )
            return slack_user
        return None


    def get_user(self, user_id):
        try:
            return SlackUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
