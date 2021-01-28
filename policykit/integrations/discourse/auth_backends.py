from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.discourse.models import DiscourseCommunity, DiscourseUser
from urllib import parse
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

class DiscourseBackend(BaseBackend):

    def authenticate(self, request, oauth=None, platform=None):
        if platform != 'discourse':
            return None

        url = request.session['discourse_url']
        api_key = request.session['discourse_api_key']

        s = DiscourseCommunity.objects.filter(team_id=url)

        if s.exists():
            req = urllib.request.Request(url + '/session/current.json')
            req.add_header("User-Api-Key", api_key)
            resp = urllib.request.urlopen(req)
            user_info = json.loads(resp.read().decode('utf-8'))['current_user']

            discourse_user = DiscourseUser.objects.filter(username=user_info['id'])

            if discourse_user.exists():
                # update user info
                discourse_user = discourse_user[0]
                discourse_user.community = s[0]
                discourse_user.password = api_key
                discourse_user.readable_name = user_info['name']
                discourse_user.avatar = user_info['avatar_template']
                discourse_user.save()
            else:
                discourse_user,_ = DiscourseUser.objects.get_or_create(
                    username = user_info['id'],
                    password = api_key,
                    community = s[0],
                    readable_name = user_info['name'],
                    avatar = user_info['avatar_template']
                )
            return discourse_user
        return None

    def get_user(self, user_id):
        try:
            return DiscourseUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
