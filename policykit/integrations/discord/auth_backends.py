from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from integrations.discord.models import DiscordCommunity, DiscordUser
from urllib import parse
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

class DiscordBackend(BaseBackend):

    def authenticate(self, request, oauth=None, platform=None):
        if not oauth or platform != "discord":
            return None

        req = urllib.request.Request('https://www.discordapp.com/api/users/@me/guilds')
        req.add_header('Authorization', 'Bearer %s' % oauth['access_token'])
        req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
        resp = urllib.request.urlopen(req)
        user_guilds = json.loads(resp.read().decode('utf-8'))

        community = None
        for guild in user_guilds:
            s = DiscordCommunity.objects.filter(team_id=guild['id'])
            if s.exists():
                community = s[0]

        if community:
            req = urllib.request.Request('https://www.discordapp.com/api/users/@me')
            req.add_header('Authorization', 'Bearer %s' % oauth['access_token'])
            req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
            resp = urllib.request.urlopen(req)
            user_info = json.loads(resp.read().decode('utf-8'))

            discord_user = DiscordUser.objects.filter(username=user_info['id'])

            if discord_user.exists():
                # update user info
                discord_user = discord_user[0]
                discord_user.community = community
                discord_user.password = oauth['access_token']
                discord_user.readable_name = user_info['username']
                discord_user.avatar = user_info['avatar']
                discord_user.save()
            else:
                discord_user,_ = DiscordUser.objects.get_or_create(
                    username = user_info['id'],
                    password = oauth['access_token'],
                    community = community,
                    readable_name = user_info['username'],
                    avatar = user_info['avatar'],
                )
            return discord_user
        return None

    def get_user(self, user_id):
        try:
            return DiscordUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
