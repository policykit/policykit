import logging

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.discord.models import DiscordCommunity, DiscordUser
import integrations.discord.utils as DiscordUtils
import requests

logger = logging.getLogger(__name__)


class DiscordBackend(BaseBackend):
    def authenticate(self, request, user_token=None, user_id=None, team_id=None):

        if not user_token or not team_id or not user_id:
            logger.error("Missing user_token or team")
            return None

        try:
            discord_community = DiscordCommunity.objects.get(team_id=team_id)
        except DiscordCommunity.DoesNotExist:
            logger.error(f"No DiscordCommunity found for {team_id}")
            return None

        # Get info about this user. We can make request directly to Discord since we have the user token.
        resp = requests.get(
            f"https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        user_data = resp.json()
        logger.debug(f"Logging in user: {user_data}")
        discord_user, created = discord_community._update_or_create_user(user_data)

        # Store the user's token. This is only necessary if we want PolicyKit to be able to make requests on their behalf later on.
        discord_user.password = user_token
        discord_user.access_token = user_token
        discord_user.save()

        logger.debug(f"{'Created' if created else 'Updated'} Discord user {discord_user}")
        return discord_user

    def get_user(self, user_id):
        try:
            return DiscordUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
