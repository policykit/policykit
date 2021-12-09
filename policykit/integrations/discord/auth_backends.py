import logging

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.discord.models import DiscordCommunity, DiscordUser
from integrations.discord.utils import get_discord_user_fields
import requests

logger = logging.getLogger(__name__)


class DiscordBackend(BaseBackend):
    def authenticate(self, request, user_token=None, user_id=None, team_id=None):

        # user_token = request.GET.get("user_token")
        # user_id = request.GET.get("user_id")
        # guilds = request.GET.getlist("guild[]")
        # # list of (id, name) tuples
        # guilds = [tuple(x.split(":", 1)) for x in guilds]
        # logger.debug(f"user belongs to guilds: {guilds}")
        # if not guilds:
        #     logger.error("PolicyKit is not installed to any of this users guilds.")
        #     return None
        
        if not user_token or not team_id or not user_id:
            logger.error("Missing user_token or team")
            return None

        try:
            discord_community = DiscordCommunity.objects.get(team_id=team_id)
        except DiscordCommunity.DoesNotExist:
            logger.error(f"No DiscordCommunity found for {team_id}")
            return None

        # Get info about this user. Can make request directly to Discord since we have the token.
        resp = requests.get(
            f"https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        user_data = resp.json()
        logger.debug(user_data)
        user_fields = get_discord_user_fields(user_data)
        logger.debug(user_fields)
        # Store the user's token. This is only necessary if we want PolicyKit to be able to make requests on their behalf later on.
        user_fields["password"] = user_token
        user_fields["access_token"] = user_token

        # FIXME
        unique_username = f"{user_data['id']}:{team_id}"

        discord_user, created = DiscordUser.objects.update_or_create(
            username=unique_username,
            community=discord_community,
            defaults=user_fields,
        )
        logger.debug(f"{'Created' if created else 'Updated'} Discord user {discord_user}")
        return discord_user

    def get_user(self, user_id):
        try:
            return DiscordUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
