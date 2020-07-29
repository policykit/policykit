from django.shortcuts import render, redirect
from django.http import HttpResponse
from policykit.settings import SERVER_URL, DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_BOT_TOKEN
from discordintegration.models import DiscordCommunity, DiscordUser, DiscordPostMessage
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
    guild_id = request.GET.get('guild_id')
    error = request.GET.get('error')

    logger.info(code)

    if error == 'access_denied':
        # error message stating that the sign-in/add-to-discord didn't work
        response = redirect('/login?error=cancel')
        return response

    data = parse.urlencode({
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SERVER_URL + '/discord/oauth'
    }).encode()

    req = urllib.request.Request('https://discordapp.com/api/oauth2/token', data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))

    logger.info(res)

    if state == 'policykit_discord_user_login':
        user = authenticate(request, oauth=res, platform='discord')
        if user:
            login(request, user)
            response = redirect('/main')
            return response
        else:
            response = redirect('/login?error=invalid_login')
            return response

    elif state == 'policykit_discord_mod_install':
        req = urllib.request.Request('https://discordapp.com/api/guilds/%s' % guild_id)
        req.add_header("Content-Type", "application/json")
        req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
        req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
        resp = urllib.request.urlopen(req)
        guild_info = json.loads(resp.read().decode('utf-8'))

        s = DiscordCommunity.objects.filter(team_id=guild_id)
        community = None
        user_group,_ = CommunityRole.objects.get_or_create(role_name="Base User", name="Discord: " + guild_info['name'] + ": Base User")

        if not s.exists():
            community = DiscordCommunity.objects.create(
                community_name=guild_info['name'],
                team_id=guild_id,
                access_token=res['access_token'],
                refresh_token=res['refresh_token'],
                base_role=user_group
            )
            user_group.community = community
            user_group.save()

            cg = CommunityDoc.objects.create(text='', community=community)
            community.community_guidelines=cg
            community.save()

            # Get the list of users and create a DiscordUser object for each user
            req = urllib.request.Request('https://discordapp.com/api/guilds/%s/members' % guild_id)
            req.add_header("Content-Type", "application/json")
            req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
            req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
            resp = urllib.request.urlopen(req)
            guild_members = json.loads(resp.read().decode('utf-8'))

            for member in guild_members:
                user, _ = DiscordUser.objects.get_or_create(username=member['user']['id'],
                        readable_name=member['user']['username'],
                        community=community)
                user.save()
        else:
            community = s[0]
            community.community_name = guild_info['name']
            community.team_id = guild_id
            community.access_token = res['access_token']
            community.refresh_token = res['refresh_token']
            community.save()

        logger.info(community.access_token)

        response = redirect('/login?success=true')
        return response

    response = redirect('/login?error=no_owned_guilds_found')
    return response

@csrf_exempt
def action(request):
    json_data = json.loads(request.body)
    logger.info('RECEIVED ACTION')
    logger.info(json_data)

def post_policy(policy, action, users=None, template=None, channel=None):
    from policyengine.models import LogAPICall

    policy_message_default = "This action is governed by the following policy: " + policy.description

    if not template:
        policy_message = policy_message_default
    else:
        policy_message = template

    data = {
        'content': policy_message
    }

    call = ('channels/%s/messages' % channel)

    res = policy.community.make_call(call, values=data)
    data['id'] = res['id']
    _ = LogAPICall.objects.create(community=community,
                                  call_type=call,
                                  extra_info=json.dumps(data))

    action.community_post = res['id']
    action.save()
