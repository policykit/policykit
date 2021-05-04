from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.discord.models import DiscordCommunity, DiscordUser
from urllib import parse
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

class DiscordBackend(BaseBackend):

    def authenticate(self, request, guild_id=None, access_token=None):
        if not guild_id or not access_token:
            return None

        community = DiscordCommunity.objects.filter(team_id=guild_id)
        if not community.exists():
            return None
        community = community[0]

        req = urllib.request.Request('https://www.discordapp.com/api/users/@me')
        req.add_header('Authorization', 'Bearer %s' % access_token)
        req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
        resp = urllib.request.urlopen(req)
        user_info = json.loads(resp.read().decode('utf-8'))

        discord_user = DiscordUser.objects.filter(username=f"{user_info['id']}:{guild_id}")

        if discord_user.exists():
            # update user info
            discord_user = discord_user[0]
            discord_user.password = access_token
            discord_user.community = community
            discord_user.readable_name = user_info['username']
            discord_user.avatar = user_info['avatar']
            discord_user.save()
        else:
            discord_user,_ = DiscordUser.objects.get_or_create(
                username = f"{user_info['id']}:{guild_id}",
                password = access_token,
                community = community,
                readable_name = user_info['username'],
                avatar = user_info['avatar'],
            )
        return discord_user

    def get_user(self, user_id):
        try:
            return DiscordUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
