from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.discourse.models import DiscourseCommunity, DiscourseUser
from integrations.discourse.utils import get_discourse_user_fields
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

        try:
            community = DiscourseCommunity.objects.get(team_id=url)
        except DiscourseCommunity.DoesNotExist:
            logger.info(f"PolicyKit not installed to community {url}")
            return None

        req = urllib.request.Request(url + '/session/current.json')
        req.add_header("User-Api-Key", api_key)
        resp = urllib.request.urlopen(req)
        user_info = json.loads(resp.read().decode('utf-8'))['current_user']


        user_fields = get_discourse_user_fields(user_info, community)
        user_fields['password'] = api_key

        discourse_user,_ = DiscourseUser.objects.update_or_create(
            community=community, username=user_info['username'],
            defaults=user_fields,
        )

        return discourse_user

    def get_user(self, user_id):
        try:
            return DiscourseUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
