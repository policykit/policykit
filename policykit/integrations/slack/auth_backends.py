import logging

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.slack.models import SlackCommunity, SlackUser
from integrations.slack.utils import get_slack_user_fields

logger = logging.getLogger(__name__)


class SlackBackend(BaseBackend):
    def authenticate(self, request, oauth=None, platform=None, user_token=None, user_id=None, team_id=None):
        if not user_token or not team_id or not user_id:
            logger.error("missing user token or team")
            return None

        if platform != "slack":
            return None

        try:
            community = SlackCommunity.objects.get(team_id=team_id)
        except SlackCommunity.DoesNotExist:
            return None

        response = community.make_call("users.info", {"user": user_id})
        user_info = response["user"]
        user_fields = get_slack_user_fields(user_info)
        user_fields["password"] = user_token
        user_fields["access_token"] = user_token

        slack_user, created = SlackUser.objects.update_or_create(
            community=community,
            username=user_info["id"],
            defaults=user_fields,
        )
        logger.debug(f"Created or updated {slack_user} (created: {created})")
        return slack_user

    def get_user(self, user_id):
        try:
            return SlackUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
