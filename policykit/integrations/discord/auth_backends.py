import logging

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.discord.models import DiscordCommunity, DiscordUser
from integrations.discord.utils import get_discord_user_fields

logger = logging.getLogger(__name__)


class DiscordBackend(BaseBackend):
    def authenticate(self, request, user_token=None, user_id=None, team_id=None):
        if not user_token or not team_id or not user_id:
            logger.error("Missing user_token or team")
            return None

        try:
            community = DiscordCommunity.objects.get(team_id=team_id)
        except DiscordCommunity.DoesNotExist:
            logger.error(f"No DiscordCommunity found for {team_id}")
            return None

        # Get info about this user
        user = discord_community.make_call("discord.get_user", {"user_id": user_id})
        user_fields = get_discord_user_fields(user)
        # Store the user's token. This is only necessary if we want PolicyKit to be able to make requests on their behalf later on.
        user_fields["password"] = user_token
        user_fields["access_token"] = user_token

        discord_user, created = DiscordUser.objects.update_or_create(
            community=community,
            username=user["id"],
            defaults=user_fields,
        )
        logger.debug(f"{'Created' if created else 'Updated'} Discord user {discord_user}")
        return discord_user

    def get_user(self, user_id):
        try:
            return DiscordUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
