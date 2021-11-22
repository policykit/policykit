import logging

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.slack.models import SlackCommunity, SlackUser
from integrations.slack.utils import get_slack_user_fields


logger = logging.getLogger(__name__)


class SlackBackend(BaseBackend):
    def authenticate(self, request):
        user_token = request.GET.get("user_token")
        user_id = request.GET.get("user_id")
        team_id = request.GET.get("team_id")
        if not user_token or not team_id or not user_id:
            logger.error("Missing user token or team")
            return None

        try:
            community = SlackCommunity.objects.get(team_id=team_id)
        except SlackCommunity.DoesNotExist:
            logger.error(f"No SlackCommunity found for {team_id}")
            return None

        # Get info about this user by hitting the Slack 'users.info' endpoint through Metagov
        response = community.metagov_plugin.method(method_name="users.info", user=user_id)
        user_info = response["user"]
        user_fields = get_slack_user_fields(user_info)
        # Store the user's token. This is only necessary if we want PolicyKit to be able to make requests on their behalf later on.
        user_fields["password"] = user_token
        user_fields["access_token"] = user_token

        slack_user, created = SlackUser.objects.update_or_create(
            community=community,
            username=user_info["id"],
            defaults=user_fields,
        )
        logger.debug(f"{'Created' if created else 'Updated'} Slack user {slack_user}")
        return slack_user

    def get_user(self, user_id):
        try:
            return SlackUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
