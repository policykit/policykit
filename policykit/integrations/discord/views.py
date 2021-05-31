from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.conf import settings
from django.contrib.auth import login, authenticate
from django.views.decorators.csrf import csrf_exempt
from policykit.settings import SERVER_URL, DISCORD_CLIENT_ID, DISCORD_CLIENT_SECRET, DISCORD_BOT_TOKEN
from policyengine.models import *
from integrations.discord.models import *
from urllib import parse
import urllib.request
import json
import base64
import logging
import websocket
import threading
import datetime
import time

logger = logging.getLogger(__name__)

websocket.enableTrace(False)

# Used for Boolean voting
EMOJI_LIKE = ['👍', '👍🏻', '👍🏼', '👍🏽', '👍🏾', '👍🏿']
EMOJI_DISLIKE = ['👎', '👎🏻', '👎🏼', '👎🏽', '👎🏾', '👎🏿']


GATEWAY_VERSION = 8

session_id = None
heartbeat_interval = None
ack_received = True
sequence_number = None

def get_gateway_uri():
    req = urllib.request.Request('https://discordapp.com/api/gateway')
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))
    return res['url']

def on_open(wsapp):
    def run(*args):
        global heartbeat_interval, ack_received, sequence_number
        while True:
            if heartbeat_interval:
                time.sleep(heartbeat_interval / 1000)

                # Verify that client received heartbeat ack between attempts at sending heartbeats
                #if ack_received == False:
                #    wsapp.close(status=1002)

                payload = json.dumps({
                    'op': 1,
                    'd': sequence_number
                })
                wsapp.send(payload)

    rt = threading.Thread(target=run)
    rt.daemon = True
    rt.start()

def should_create_action(message, type=None):
    if type == None:
        logger.error('type parameter not specified in should_create_action')
        return False

    created_at = None

    if type == "MESSAGE_CREATE":
        # If message already has an object, don't create a new object for it.
        # We only filter on message IDs because they are generated using Twitter
        # snowflakes which are universally unique across all Discord servers.
        if DiscordPostMessage.objects.filter(message_id=message['id']).exists():
            return False

        created_at = message['timestamp'] # ISO8601 timestamp
        created_at = datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%f+00:00")

    if created_at == None:
        logger.error("created_at is None when it shouldn't be in should_create_action")
        return False

    now = datetime.datetime.now()

    # If action is more than twice the Celery beat frequency seconds old,
    # don't create an object for it. This way, we only create objects for
    # actions taken after PolicyKit has been installed to the community.
    recent_time = 2 * settings.CELERY_BEAT_FREQUENCY
    if now - created_at > datetime.timedelta(seconds=recent_time):
        return False
    return True

def handle_ready_event(data):
    global session_id
    session_id = data['session_id']

def handle_guild_create_event(data):
    # Populate the DiscordChannel objects
    for channel in data['channels']:
        c = DiscordChannel.objects.filter(channel_id=channel['id'])
        if c.exists():
            c = c[0]
            c.channel_name = channel['name']
            c.save()
        else:
            c = DiscordChannel.objects.create(
                guild_id=data['id'],
                channel_id=channel['id'],
                channel_name=channel['name']
            )
    logger.info(f'Populated DiscordChannel objects from GUILD_CREATE event')

def handle_message_create_event(data):
    if should_create_action(data, type="MESSAGE_CREATE"):
        channel = DiscordChannel.objects.filter(channel_id=data['channel_id'])[0]
        guild_id = channel.guild_id
        community = DiscordCommunity.objects.filter(team_id=guild_id)[0]

        action = DiscordPostMessage()
        action.community = community
        action.text = data['content']
        action.channel_id = data['channel_id']
        action.message_id = data['id']

        u,_ = DiscordUser.objects.get_or_create(
            username=f"{data['author']['id']}:{guild_id}",
            community=community
        )
        action.initiator = u

        logger.info(f'New message in channel {channel.channel_name}: {data["content"]}')

        return action

def handle_message_delete_event(data):
    channel = DiscordChannel.objects.filter(channel_id=data['channel_id'])[0]
    guild_id = channel.guild_id
    community = DiscordCommunity.objects.filter(team_id=guild_id)[0]

    # Gets the channel message
    message = community.make_call(f"channels/{data['channel_id']}/messages/{data['id']}")

    action = DiscordDeleteMessage()
    action.community = community
    action.channel_id = data['channel_id']
    action.message_id = data['id']

    u,_ = DiscordUser.objects.get_or_create(
        username=f"{message['author']['id']}:{guild_id}",
        community=community
    )
    action.initiator = u

    logger.info(f'Message deleted in channel {channel.channel_name}: {message["content"]}')

    return action

def handle_channel_update_event(data):
    guild_id = data['guild_id']
    community = DiscordCommunity.objects.filter(team_id=guild_id)[0]

    action = DiscordRenameChannel()
    action.community = community
    action.channel_id = data['id']
    action.name = data['name']

    # FIXME: User who changed channel name not passed along with CHANNEL_UPDATE
    # event. All PlatformActions require an initiator in PolicyKit, so as a
    # placeholder, the Discord client ID is set as the initiator.
    # However, this is not accurate and should be changed in the future
    # if and when possible.
    u,_ = DiscordUser.objects.get_or_create(
        username=f"{DISCORD_CLIENT_ID}:{guild_id}",
        community=community
    )
    action.initiator = u

    channel = DiscordChannel.objects.filter(channel_id=data['id'])[0]
    logger.info(f'Channel {channel.channel_name} renamed to {action.name}')

    # Update DiscordChannel object
    channel.channel_name = action.name
    channel.save()

    return action

def handle_channel_create_event(data):
    guild_id = data['guild_id']
    community = DiscordCommunity.objects.filter(team_id=guild_id)[0]

    # Create new DiscordChannel object
    DiscordChannel.objects.get_or_create(
        guild_id=guild_id,
        channel_id=data['id'],
        channel_name=data['name']
    )

    action = DiscordCreateChannel()
    action.community = community
    action.guild_id = guild_id
    action.name = data['name']

    # FIXME: Same issue as in handle_channel_update_event()
    u,_ = DiscordUser.objects.get_or_create(
        username=f"{DISCORD_CLIENT_ID}:{guild_id}",
        community=community
    )
    action.initiator = u

    logger.info(f'Channel created: {action.name}')

    return action

def handle_channel_delete_event(data):
    guild_id = data['guild_id']
    community = DiscordCommunity.objects.filter(team_id=guild_id)[0]

    action = DiscordDeleteChannel()
    action.community = community
    action.channel_id = data['id']

    # FIXME: Same issue as in handle_channel_update_event()
    u,_ = DiscordUser.objects.get_or_create(
        username=f"{DISCORD_CLIENT_ID}:{guild_id}",
        community=community
    )
    action.initiator = u

    logger.info(f'Channel deleted: {data["name"]}')

    return action

def handle_event(name, data):
    if name == 'READY':
        handle_ready_event(data)
    elif name == 'GUILD_CREATE':
        handle_guild_create_event(data)
    else:
        action = None

        if name == 'MESSAGE_CREATE':
            action = handle_message_create_event(data)
        elif name == 'MESSAGE_DELETE':
            action = handle_message_delete_event(data)
        elif name == 'CHANNEL_UPDATE':
            action = handle_channel_update_event(data)
        elif name == 'CHANNEL_CREATE':
            action = handle_channel_create_event(data)
        elif name == 'CHANNEL_DELETE':
            action = handle_channel_delete_event(data)

        if action:
            action.community_origin = True
            action.is_bundled = False
            action.save()

            # While consider_proposed_actions will execute every Celery beat,
            # we don't want to wait for the beat since using websockets we can
            # know right away when an event is triggered in Discord. Thus, we
            # manually call consider_proposed_actions whenever we have a new
            # proposed action in Discord.
            from policyengine.tasks import consider_proposed_actions
            consider_proposed_actions()

        if name == 'MESSAGE_REACTION_ADD':
            action_res = PlatformAction.objects.filter(community_post=data['message_id'])
            action_res = action_res or ConstitutionAction.objects.filter(community_post=data['message_id'])
            # logger.debug(action_res.get())
            if action_res.exists():
                action = action_res[0]
                reaction = data['emoji']['name']
                if reaction in (EMOJI_LIKE + EMOJI_DISLIKE):
                    val = (reaction in EMOJI_LIKE)
                    user = DiscordUser.objects.get(username=f"{data['user_id']}:{data['guild_id']}",
                                                               community=action.community)
                    vote = BooleanVote.objects.filter(proposal=action.proposal, user=user)

                    if vote.exists():
                        vote = vote[0]
                        vote.boolean_value = val
                        vote.save()

                    else:
                        vote = BooleanVote.objects.create(proposal=action.proposal,
                                                          user=user,
                                                          boolean_value=val)


def on_message(wsapp, message):
    global heartbeat_interval, sequence_number, ack_received
    payload = json.loads(message)
    op = payload['op']
    if op == 0: # Opcode 0 Dispatch
        logger.info(f'Received event named {payload["t"]}')
        sequence_number = payload['s']
        handle_event(payload['t'], payload['d'])
    elif op == 10: # Opcode 10 Hello
        # Receive heartbeat interval
        heartbeat_interval = payload['d']['heartbeat_interval']
        logger.info(f'Received heartbeat of {heartbeat_interval} ms from the Discord gateway')

        # Send an Opcode 2 Identify
        payload = json.dumps({
            'op': 2,
            'd': {
                'token': DISCORD_BOT_TOKEN,
                'intents': 1543,
                'properties': {
                    '$os': 'linux', # TODO: Replace with system operating system
                    '$browser': 'disco',
                    '$device': 'disco'
                },
                'compress': False
            }
        })
        wsapp.send(payload)
        logger.info('Sent an Opcode 2 Identify to the Discord gateway')
    elif op == 11: # Opcode 11 Heartbeat ACK
        ack_received = True

def on_error(wsapp, error):
    logger.error(f'Websocket error: {error}')

def on_close(wsapp, code, reason):
    logger.error(f'Connection to Discord gateway closed with error code {code}')

# Open gateway connection
def connect_gateway():
    wsapp = websocket.WebSocketApp(f'{get_gateway_uri()}?v={GATEWAY_VERSION}&encoding=json',
        on_message=on_message,
        on_error=on_error,
        on_close=on_close)
    wsapp.on_open = on_open
    wst = threading.Thread(target=wsapp.run_forever)
    wst.daemon = True
    wst.start()

connect_gateway()

def oauth(request):
    state = request.GET.get('state')
    code = request.GET.get('code')
    guild_id = request.GET.get('guild_id')
    error = request.GET.get('error')

    if error == 'access_denied':
        return redirect('/login?error=sign_in_failed')

    data = parse.urlencode({
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SERVER_URL + '/discord/oauth'
    }).encode()

    req = urllib.request.Request('https://discordapp.com/api/oauth2/token', data=data)
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("User-Agent", "Mozilla/5.0")
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))

    if state == 'policykit_discord_user_login':
        access_token = res['access_token']

        req = urllib.request.Request('https://www.discordapp.com/api/users/@me/guilds')
        req.add_header('Authorization', 'Bearer %s' % access_token)
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req)
        guilds = json.loads(resp.read().decode('utf-8'))

        integrated_guilds = []
        for g in guilds:
            s = DiscordCommunity.objects.filter(team_id=g['id'])
            if s.exists():
                integrated_guilds.append((g['id'], g['name']))

        if len(integrated_guilds) == 0:
            return redirect('/login?error=no_policykit_integrated_guilds_found')
        elif len(integrated_guilds) == 1:
            return auth(request, guild_id=integrated_guilds[0][0], access_token=access_token)
        else:
            # If user has more than one PK-integrated Discord guild, bring user to screen to select which guild's dashboard to login to
            return render(request, "policyadmin/configure_discord.html", { "integrated_guilds": integrated_guilds, "access_token": access_token })

    elif state == 'policykit_discord_mod_install':
        req = urllib.request.Request('https://discordapp.com/api/guilds/%s' % guild_id)
        req.add_header("Content-Type", "application/json")
        req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req)
        guild_info = json.loads(resp.read().decode('utf-8'))

        s = DiscordCommunity.objects.filter(team_id=guild_id)
        community = None
        user_group,_ = CommunityRole.objects.get_or_create(role_name="Base User", name="Discord: " + guild_info['name'] + ": Base User")

        if not s.exists():
            community = DiscordCommunity.objects.create(
                community_name=guild_info['name'],
                team_id=guild_id,
                base_role=user_group
            )
            user_group.community = community
            user_group.save()

            # Get the list of users and create a DiscordUser object for each user
            guild_members = community.make_call(f'guilds/{guild_id}/members?limit=1000')

            owner_id = guild_info['owner_id']
            for member in guild_members:
                user, _ = DiscordUser.objects.get_or_create(
                    username=f"{member['user']['id']}:{guild_id}",
                    readable_name=member['user']['username'],
                    avatar=f"https://cdn.discordapp.com/avatars/{member['user']['id']}/{member['user']['avatar']}.png",
                    community=community,
                    is_community_admin=(member['user']['id'] == owner_id)
                )
                user.save()
        else:
            community = s[0]
            community.community_name = guild_info['name']
            community.team_id = guild_id
            community.save()

            return redirect('/login?success=true')

        context = {
            "starterkits": [kit.name for kit in DiscordStarterKit.objects.all()],
            "community_name": community.community_name,
            "platform": "discord"
        }
        return render(request, "policyadmin/init_starterkit.html", context)

    return redirect('/login?error=no_owned_guilds_found')

@csrf_exempt
def auth(request, guild_id=None, access_token=None):
    if not guild_id: # Redirected from Configure page
        guild_id = request.POST['guild_id']
        if not guild_id:
            return redirect('/login?error=guild_id_missing')

    if not access_token: # Redirected from Configure page
        access_token = request.POST['access_token']
        if not access_token:
            return redirect('/login?error=access_token_missing')

    user = authenticate(request, guild_id=guild_id, access_token=access_token)
    if user:
        login(request, user)
        return redirect('/main')
    else:
        return redirect('/login?error=invalid_login')

def post_policy(policy, action, users=None, template=None, channel=None):
    message = "This action is governed by the following policy: " + policy.name
    if template:
        message = template

    # User can input either channel_id or channel_name as channel parameter.
    # Here, we must check whether the user entered a valid channel_id. If not,
    # we check if the user entered a valid channel_name.
    channel_id = None
    c = DiscordChannel.objects.filter(channel_id=channel)
    if c.exists():
        channel_id = c[0].channel_id
    else:
        c = DiscordChannel.objects.filter(guild_id=policy.community.team_id, channel_name=channel)
        if c.exists():
            channel_id = c[0].channel_id
    if channel_id == None:
        return

    res = policy.community.make_call(f'channels/{channel_id}/messages', values={'content': message})

    if action.action_type == "ConstitutionAction" or action.action_type == "PlatformAction":
        action.community_post = res['id']
        action.save()
