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

    def authenticate(self, request, oauth=None, platform=None, user_token=None, team_id=None):
        if not user_token or not team_id:
            logger.error("missing user token or team")
            return None

        if platform != 'slack':
            return None

        s = SlackCommunity.objects.filter(team_id=team_id)

        if s.exists():
            data = parse.urlencode({'token': user_token}).encode()
            req = urllib.request.Request('https://slack.com/api/users.identity', data=data)
            resp = urllib.request.urlopen(req)
            user_info = json.loads(resp.read().decode('utf-8'))
            logger.info(user_info)
            slack_user = SlackUser.objects.filter(username=user_info['user']['id'])

            if slack_user.exists():
                # update user info
                slack_user = slack_user[0]
                slack_user.access_token = user_token
                slack_user.community = s[0]
                slack_user.password = user_token
                slack_user.readable_name = user_info['user']['name']
                slack_user.avatar = user_info['user']['image_24']
                slack_user.save()
            else:
                slack_user,_ = SlackUser.objects.get_or_create(
                    username = user_info['user']['id'],
                    password = user_token,
                    community = s[0],
                    readable_name = user_info['user']['name'],
                    avatar = user_info['user']['image_24'],
                    access_token = user_token,
                )
            return slack_user
        return None


    def get_user(self, user_id):
        try:
            return SlackUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
