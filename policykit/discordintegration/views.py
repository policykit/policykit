from django.shortcuts import render, redirect
from policykit.settings import SERVER_URL, DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET
from discordintegration.models import DiscordCommunity, DiscordUser
from policyengine.models import *
from django.contrib.auth import login, authenticate
from django.views.decorators.csrf import csrf_exempt
from urllib import parse
import urllib.request
import json
import base64
import logging

logger = logging.getLogger(__name__)

# Create your views here.

def oauth(request):
    logger.info(request)

    state = request.GET.get('state')
    code = request.GET.get('code')

    logger.info(code)

    data = parse.urlencode({
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SERVER_URL + '/discord/oauth'
    }).encode()

    req = urllib.request.Request('https://discordapp.com/api/oauth2/token', data=data)

    credentials = ('%s:%s' % (DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET))
    encoded_credentials = base64.b64encode(credentials.encode('ascii'))

    req.add_header("Authorization", "Basic %s" % encoded_credentials.decode("ascii"))

    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))

    logger.info(res)

    if state == 'policykit_discord_user_login':
        user = authenticate(request, oauth=res, platform='discord')
        if user:
            login(request, user)
            response = redirect('/')
            return response
        else:
            response = redirect('/login?error=invalid_login')
            return response

    elif state == 'policykit_discord_mod_install':
        req = urllib.request.Request('https://discord.com/api/users/@me/guilds')
        req.add_header('Authorization', 'bearer %s' % res['access_token'])
        resp = urllib.request.urlopen(req)
        user_guilds = json.loads(resp.read().decode('utf-8'))

        logger.info(user_guilds)

        owned_guilds = []
        for guild in user_guilds:
            if guild['owner']:
                owned_guilds.append((guild['id'], guild['name']))

        if len(owned_guilds) > 0:
            context = {
                'platform': 'discord',
                'guilds': owned_guilds,
                'access_token': res['access_token'],
                'refresh_token': res['refresh_token']
            }
            return render(request, 'policyadmin/configure.html', context)

    response = redirect('/login?error=no_owned_guilds_found')
    return response

@csrf_exempt
def initCommunity(request):
    guild_id, guild_name = request.POST['guild'].split(':', 1)
    access_token = request.POST['access_token']
    refresh_token = request.POST['refresh_token']

    s = DiscordCommunity.objects.filter(team_id=guild_id)

    community = None
    user_group,_ = CommunityRole.objects.get_or_create(role_name="Base User", name="Discord: " + guild_name + ": Base User")

    if not s.exists():
        community = DiscordCommunity.objects.create(
            community_name=guild_name,
            team_id=guild_id,
            access_token=access_token,
            refresh_token=refresh_token,
            base_role=user_group
        )
        user_group.community = community
        user_group.save()

        cg = CommunityDoc.objects.create(text='', community=community)
        community.community_guidelines=cg
        community.save()

    else:
        community = s[0]
        community.community_name = guild_name
        community.team_id = guild_id
        community.access_token = access_token
        community.refresh_token = refresh_token
        community.save()

    logger.info(community.access_token)

    response = redirect('/login?success=true')
    return response

@csrf_exempt
def action(request):
    json_data = json.loads(request.body)
    logger.info('RECEIVED ACTION')
    logger.info(json_data)
