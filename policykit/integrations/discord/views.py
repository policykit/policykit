import logging
import requests

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from integrations.discord.models import DiscordCommunity, DiscordUser
from integrations.discord.utils import get_discord_user_fields
from policyengine.models import Community, CommunityRole
from policyengine.utils import get_starterkits_info

logger = logging.getLogger(__name__)


def discord_login(request):
    """redirect after metagov has gotten the discord user token"""
    logger.debug(f"discord_login: {request.GET}")

    if request.GET.get("error"):
        return redirect(f"/login?error={request.GET.get('error')}")

    user_token = request.GET.get("user_token")
    user_id = request.GET.get("user_id")
    team_id = request.GET.get("team_id")
    user = authenticate(request, user_token=user_token, user_id=user_id, team_id=team_id)
    if user:
        login(request, user)
        return redirect("/main")

    # Note: this is not always an accurate error message.
    return redirect("/login?error=policykit_not_yet_installed_to_that_community")


def discord_install(request):
    logger.debug(f"Discord installation completed: {request.GET}")

    # metagov identifier for the "parent community" to install Discord to
    metagov_community_slug = request.GET.get("community")
    is_new_community = False
    try:
        community = Community.objects.get(metagov_slug=metagov_community_slug)
    except Community.DoesNotExist:
        logger.debug(f"Community not found: {metagov_community_slug}, creating it")
        is_new_community = True
        community = Community.objects.create(metagov_slug=metagov_community_slug)

    # if we're enabling an integration for an existing community, so redirect to the settings page
    redirect_route = "/login" if is_new_community else "/main/settings"

    expected_state = request.session.get("community_install_state")
    if expected_state is None or request.GET.get("state") is None or (not request.GET.get("state") == expected_state):
        logger.error(f"expected {expected_state}")
        return redirect(f"{redirect_route}?error=bad_state")

    if request.GET.get("error"):
        return redirect(f"{redirect_route}?error={request.GET.get('error')}")

    # TODO(issue): stop passing user id and token
    user_id = request.GET.get("user_id")
    user_token = request.GET.get("user_token")

    # Get guild info from Discord
    response = requests.post(
        f"{settings.METAGOV_URL}/api/internal/action/discord.get-guild",
        json={"parameters": {"guild_id": guild_id}},
        headers={"X-Metagov-Community": metagov_community_slug},
    )
    if not response.ok:
        return redirect(f"{redirect_route}?error=server_error")
    guild_info = response.json()
    team_id = guild_info['id']
    readable_name = guild_info['name']

    # Set readable_name for Community
    if not community.readable_name:
        community.readable_name = readable_name
        community.save()

    user_group, _ = CommunityRole.objects.get_or_create(
        role_name="Base User", name="Discord: " + readable_name + ": Base User"
    )

<<<<<<< HEAD
    discord_community = DiscordCommunity.objects.filter(team_id=team_id).first()
    if discord_community is None:
        logger.debug(f"Creating new DiscordCommunity under {community}")
        discord_community = DiscordCommunity.objects.create(
            community=community,
            community_name=readable_name,
            team_id=team_id,
            base_role=user_group,
        )
        user_group.community = discord_community
        user_group.save()

        # Get the list of users and create a DiscordUser object for each user
        guild_members = discord_community.make_call(f'guilds/{team_id}/members?limit=1000')
        owner_id = guild_info['owner_id']
        for member in guild_members:
            u, _ = DiscordUser.objects.get_or_create(
                username=member['user']['id'],
                readable_name=member['user']['username'],
                avatar=f"https://cdn.discordapp.com/avatars/{member['user']['id']}/{member['user']['avatar']}.png",
                community=discord_community,
=======
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
        # elif name == 'MESSAGE_DELETE':
        #     action = handle_message_delete_event(data)
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
            proposal = Proposal.objects.filter(
                community_post=data['message_id'],
                status=Proposal.PROPOSED
            ).first()
            if proposal:
                action = proposal.action
                reaction = data['emoji']['name']
                if reaction in [EMOJI_LIKE, EMOJI_DISLIKE]:
                    val = (reaction == EMOJI_LIKE)
                    user = DiscordUser.objects.get(username=f"{data['user_id']}:{data['guild_id']}",
                                                               community=action.community)
                    vote = BooleanVote.objects.filter(proposal=proposal, user=user)

                    if vote.exists():
                        vote = vote[0]
                        vote.boolean_value = val
                        vote.save()

                    else:
                        vote = BooleanVote.objects.create(proposal=proposal,
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

if DISCORD_CLIENT_ID:
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
            parent_community = Community.objects.create(readable_name=guild_info['name'])
            community = DiscordCommunity.objects.create(
                community_name=guild_info['name'],
                community=parent_community,
                team_id=guild_id,
                base_role=user_group
>>>>>>> 626a754c65d41d9677aeb8165d8a905f963645c8
            )
            if user_token and user_id and member['user']['id'] == user_id:
                logger.debug(f"Storing access_token for installing user ({user_id})")
                u.is_community_admin = True
                u.access_token = user_token
                u.save()

        context = {
            "server_url": SERVER_URL,
            "starterkits": get_starterkits_info(),
<<<<<<< HEAD
            "community_name": discord_community.community_name,
            "creator_token": user_token,
            "platform": "discord",
            # redirect to settings page or login page depending on whether it's a new community
            "redirect": redirect_route
=======
            "community_id": community.pk,
            "platform": "discord"
>>>>>>> 626a754c65d41d9677aeb8165d8a905f963645c8
        }
        return render(request, "policyadmin/init_starterkit.html", context)

    else:
        logger.debug("community already exists, updating name..")
        discord_community.community_name = readable_name
        discord_community.save()
        discord_community.community.readable_name = readable_name
        discord_community.community.save()

        # Store token for the user who (re)installed Discord
        if user_token and user_id:
            installer = DiscordUser.objects.filter(community=discord_community, username=user_id).first()
            if installer is not None:
                logger.debug(f"Storing access_token for installing user ({user_id})")
                installer.is_community_admin = True
                installer.access_token = user_token
                installer.save()
            else:
                logger.debug(f"User '{user_id}' is re-installing but no DiscordUser exists for them, creating one..")
                user = discord_community.make_call("discord.get_user", {"user_id": user_id})
                user_fields = get_discord_user_fields(user)
                user_fields["is_community_admin"] = True
                user_fields["access_token"] = user_token
                DiscordUser.objects.update_or_create(
                    community=discord_community,
                    username=user_id,
                    defaults=user_fields,
                )

        return redirect(f"{redirect_route}?success=true")


"""
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
<<<<<<< HEAD
"""
=======

def initiate_action_vote(proposal, users=None, template=None, channel=None):
    policy = proposal.policy
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

    res = policy.community.post_message(text=message, channel=channel_id)

    proposal.community_post = res['id']
    proposal.save()

    time.sleep(1)
    policy.community.make_call(f'channels/{channel_id}/messages/{res["id"]}/reactions/%F0%9F%91%8D/@me', method="PUT")
    time.sleep(1)
    policy.community.make_call(f'channels/{channel_id}/messages/{res["id"]}/reactions/%F0%9F%91%8E/@me', method="PUT")
>>>>>>> 626a754c65d41d9677aeb8165d8a905f963645c8
