import logging

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.opencollective.models import OpenCollectiveCommunity, OpencollectiveUser

import requests

logger = logging.getLogger(__name__)


class DiscordBackend(BaseBackend):
    def authenticate(self, request, user_token=None, user_id=None, team_id=None):

        
        # if not user_token or not team_id or not user_id:
        #     logger.error("Missing user_token or team")
        #     return None

        try:
            oc_community = OpenCollectiveCommunity.objects.get(team_id=team_id)
        except OpenCollectiveCommunity.DoesNotExist:
            logger.error(f"No OpenCollectiveCommunity found for {team_id}")
            return None

        # FIXME
        return oc_community.users.first

    def get_user(self, user_id):
        try:
            return OpencollectiveUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
