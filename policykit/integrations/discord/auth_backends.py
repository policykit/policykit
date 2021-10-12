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
            discord_community = DiscordCommunity.objects.get(team_id=team_id)
        except DiscordCommunity.DoesNotExist:
            logger.error(f"No DiscordCommunity found for {team_id}")
            return None
# <<<<<<< HEAD
#         community = community[0]

#         req = urllib.request.Request('https://www.discordapp.com/api/users/@me')
#         req.add_header('Authorization', 'Bearer %s' % access_token)
#         req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
#         resp = urllib.request.urlopen(req)
#         user_info = json.loads(resp.read().decode('utf-8'))

#         discord_user = DiscordUser.objects.filter(username=f"{user_info['id']}:{guild_id}")

#         from integrations.discord.views import avatar_url
#         if discord_user.exists():
#             # update user info
#             discord_user = discord_user[0]
#             discord_user.password = access_token
#             discord_user.community = community
#             discord_user.readable_name = user_info['username']
#             discord_user.avatar = avatar_url(user_info)
#             discord_user.save()
#         else:
#             discord_user,_ = DiscordUser.objects.get_or_create(
#                 username = f"{user_info['id']}:{guild_id}",
#                 password = access_token,
#                 community = community,
#                 readable_name = user_info['username'],
#                 avatar = avatar_url(user_info)
#             )
# =======

        # Get info about this user
        user = discord_community.make_call("discord.get_user", {"user_id": user_id})
        user_fields = get_discord_user_fields(user)
        # Store the user's token. This is only necessary if we want PolicyKit to be able to make requests on their behalf later on.
        user_fields["password"] = user_token
        user_fields["access_token"] = user_token

        discord_user, created = DiscordUser.objects.update_or_create(
            community=discord_community,
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
