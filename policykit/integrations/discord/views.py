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
from policyengine.metagov_app import metagov
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)


def discord_login(request):
    """redirect after metagov has gotten the discord user token"""
    logger.debug(f"discord_login: {request.GET}")

    if request.GET.get("error"):
        return redirect(f"/login?error={request.GET.get('error')}")

    user_token = request.GET.get("user_token")
    user_id = request.GET.get("user_id")
    guilds = request.GET.getlist("guild[]")
    # list of (id, name) tuples
    guilds = [tuple(x.split(":", 1)) for x in guilds]
    logger.debug(f"user belongs to guilds: {guilds}")

    if not guilds:
        return redirect("/login?error=no_policykit_integrated_guilds_found")
    elif len(guilds) == 1:
        user = authenticate(
            request,
            team_id=guilds[0][0],
            user_token=user_token,
            user_id=user_id,
        )
        if user:
            login(request, user)
            return redirect("/main")
    else:
        # If user has more than one PK-integrated Discord guild, bring user to screen to select which guild's dashboard to login to
        request.session['user_id'] = 'user_id'
        request.session['user_token'] = 'user_token'
        return render(
            request, "policyadmin/configure_discord.html", {"integrated_guilds": guilds, "access_token": user_token}
        )

    # Note: this is not always an accurate error message.
    return redirect("/login?error=policykit_not_yet_installed_to_that_community")


def login_selected_guild(request):
    """
    This view only gets hit after user completes the configure_discord.html form.
    This only applies for users that have multiple guilds set up with PolicyKit.
    """
    guild_id = request.POST['guild_id']
    if not guild_id:
        return redirect('/login?error=guild_id_missing')

    user_id = request.session.get('user_id')
    user_token = request.session.get('user_token')
    if not user_token or user_id:
        return redirect('/login?error=user_info_missing')

    user = authenticate(request, team_id=guild_id, user_id=user_id, user_token=user_token)
    if user:
        login(request, user)
        return redirect('/main')
    else:
        return redirect('/login?error=invalid_login')

# def handle_channel_update_event(data):
#     guild_id = data['guild_id']
#     community = DiscordCommunity.objects.filter(team_id=guild_id)[0]

#     action = DiscordRenameChannel()
#     action.community = community
#     action.channel_id = data['id']
#     action.name = data['name']

#     # FIXME: User who changed channel name not passed along with CHANNEL_UPDATE
#     # event. All GovernableActions require an initiator in PolicyKit, so as a
#     # placeholder, the Discord client ID is set as the initiator.
#     # However, this is not accurate and should be changed in the future
#     # if and when possible.
#     u,_ = DiscordUser.objects.get_or_create(
#         username=f"{DISCORD_CLIENT_ID}:{guild_id}",
#         community=community
#     )
#     action.initiator = u

#     channel = DiscordChannel.objects.filter(channel_id=data['id'])[0]
#     logger.info(f'Channel {channel.channel_name} renamed to {action.name}')

#     # Store old name on action, in case we need to revert it
#     action.name_old = channel.channel_name

#     # Update DiscordChannel object
#     channel.channel_name = action.name
#     channel.save()

#     return action

# def handle_channel_create_event(data):
#     guild_id = data['guild_id']
#     community = DiscordCommunity.objects.filter(team_id=guild_id)[0]

#     # Create new DiscordChannel object
#     DiscordChannel.objects.get_or_create(
#         guild_id=guild_id,
#         channel_id=data['id'],
#         channel_name=data['name']
#     )

#     action = DiscordCreateChannel()
#     action.community = community
#     action.guild_id = guild_id
#     action.name = data['name']

#     # FIXME: Same issue as in handle_channel_update_event()
#     u,_ = DiscordUser.objects.get_or_create(
#         username=f"{DISCORD_CLIENT_ID}:{guild_id}",
#         community=community
#     )
#     action.initiator = u

#     logger.info(f'Channel created: {action.name}')

#     return action

# def handle_channel_delete_event(data):
#     guild_id = data['guild_id']
#     community = DiscordCommunity.objects.filter(team_id=guild_id)[0]

#     action = DiscordDeleteChannel()
#     action.community = community
#     action.channel_id = data['id']

#     # FIXME: Same issue as in handle_channel_update_event()
#     u,_ = DiscordUser.objects.get_or_create(
#         username=f"{DISCORD_CLIENT_ID}:{guild_id}",
#         community=community
#     )
#     action.initiator = u

#     logger.info(f'Channel deleted: {data["name"]}')

#     return action

# def handle_event(name, data):
#     if name == 'READY':
#         handle_ready_event(data)
#     elif name == 'GUILD_CREATE':
#         handle_guild_create_event(data)
#     else:
#         action = None

#         if name == 'MESSAGE_CREATE':
#             action = handle_message_create_event(data)
#         # elif name == 'MESSAGE_DELETE':
#         #     action = handle_message_delete_event(data)
#         elif name == 'CHANNEL_UPDATE':
#             action = handle_channel_update_event(data)
#         elif name == 'CHANNEL_CREATE':
#             action = handle_channel_create_event(data)
#         elif name == 'CHANNEL_DELETE':
#             action = handle_channel_delete_event(data)

#         if action:
#             action.community_origin = True
#             action.save()

#             # While consider_proposed_actions will execute every Celery beat,
#             # we don't want to wait for the beat since using websockets we can
#             # know right away when an event is triggered in Discord. Thus, we
#             # manually call consider_proposed_actions whenever we have a new
#             # proposed action in Discord.
#             from policyengine.tasks import consider_proposed_actions
#             consider_proposed_actions()

#         if name == 'MESSAGE_REACTION_ADD':
#             proposal = Proposal.objects.filter(
#                 community_post=data['message_id'],
#                 status=Proposal.PROPOSED
#             ).first()
#             if proposal:
#                 action = proposal.action
#                 reaction = data['emoji']['name']
#                 if reaction in [EMOJI_LIKE, EMOJI_DISLIKE]:
#                     val = (reaction == EMOJI_LIKE)
#                     user = DiscordUser.objects.get(username=f"{data['user_id']}:{data['guild_id']}",
#                                                                community=action.community)
#                     vote = BooleanVote.objects.filter(proposal=proposal, user=user)

#                     if vote.exists():
#                         vote = vote[0]
#                         vote.boolean_value = val
#                         vote.save()

#                     else:
#                         vote = BooleanVote.objects.create(proposal=proposal,
#                                                           user=user,
#                                                           boolean_value=val)


# def on_message(wsapp, message):
#     global heartbeat_interval, sequence_number, ack_received
#     payload = json.loads(message)
#     op = payload['op']
#     if op == 0: # Opcode 0 Dispatch
#         logger.info(f'Received event named {payload["t"]}')
#         sequence_number = payload['s']
#         handle_event(payload['t'], payload['d'])
#     elif op == 10: # Opcode 10 Hello
#         # Receive heartbeat interval
#         heartbeat_interval = payload['d']['heartbeat_interval']
#         logger.info(f'Received heartbeat of {heartbeat_interval} ms from the Discord gateway')

#         # Send an Opcode 2 Identify
#         payload = json.dumps({
#             'op': 2,
#             'd': {
#                 'token': DISCORD_BOT_TOKEN,
#                 'intents': 1543,
#                 'properties': {
#                     '$os': 'linux', # TODO: Replace with system operating system
#                     '$browser': 'disco',
#                     '$device': 'disco'
#                 },
#                 'compress': False
#             }
#         })
#         wsapp.send(payload)
#         logger.info('Sent an Opcode 2 Identify to the Discord gateway')
#     elif op == 11: # Opcode 11 Heartbeat ACK
#         ack_received = True

# def on_error(wsapp, error):
#     logger.error(f'Websocket error: {error}')

# def on_close(wsapp, code, reason):
#     logger.error(f'Connection to Discord gateway closed with error code {code}')

# # Open gateway connection
# def connect_gateway():
#     wsapp = websocket.WebSocketApp(f'{get_gateway_uri()}?v={GATEWAY_VERSION}&encoding=json',
#         on_message=on_message,
#         on_error=on_error,
#         on_close=on_close)
#     wsapp.on_open = on_open
#     wst = threading.Thread(target=wsapp.run_forever)
#     wst.daemon = True
#     wst.start()

# if DISCORD_CLIENT_ID:
#     connect_gateway()





def discord_install(request):
    """
    Gets called after the oauth install flow is completed. This is the redirect_uri that was passed to the oauth flow.
    """
    logger.debug(f"Discord installation completed: {request.GET}")

    # metagov identifier for the "parent community" to install Discord to
    metagov_community_slug = request.GET.get("community")
    community, is_new_community = Community.objects.get_or_create(metagov_slug=metagov_community_slug)

    # if we're enabling an integration for an existing community, so redirect to the settings page
    redirect_route = "/login" if is_new_community else "/main/settings"

    if request.GET.get("error"):
        return redirect(f"{redirect_route}?error={request.GET.get('error')}")

    # TODO(issue): stop passing user id and token
    user_id = request.GET.get("user_id")
    user_token = request.GET.get("user_token")
    guild_id = request.GET.get("guild_id")

    # Fetch guild info to get the guild name
    # TODO: catch Plugin.DoesNotExist
    mg_community = metagov.get_community(community.metagov_slug)
    discord_plugin = mg_community.get_plugin("discord", guild_id)
    guild_info = discord_plugin.get_guild()
    guild_name = guild_info["name"]

    discord_community = DiscordCommunity.objects.filter(team_id=guild_id).first()
    if discord_community is None:
        logger.debug(f"Creating new DiscordCommunity for guild '{guild_name}' under {community}")
        discord_community = DiscordCommunity.objects.create(
            community=community,
            community_name=guild_name,
            team_id=guild_id,
        )

        # Get the list of users and create a DiscordUser object for each user
        """
        guild_members = discord_community.make_call(f'guilds/{guild_id}/members?limit=1000')
        owner_id = guild_info['owner_id']
        for member in guild_members:
            u, _ = DiscordUser.objects.get_or_create(
                username=member['user']['id'],
                readable_name=member['user']['username'],
                avatar=f"https://cdn.discordapp.com/avatars/{member['user']['id']}/{member['user']['avatar']}.png",
                community=discord_community,
            )
            if user_token and user_id and member['user']['id'] == user_id:
                logger.debug(f"Storing access_token for installing user ({user_id})")
                u.is_community_admin = True
                u.access_token = user_token
                u.save()
        """

        if is_new_community:
            context = {
                "server_url": settings.SERVER_URL,
                "starterkits": get_starterkits_info(),
                "community_id": discord_community.community.pk,
                "creator_token": user_token,
            }
            return render(request, "policyadmin/init_starterkit.html", context)
        else:
            return redirect(f"{redirect_route}?success=true")

    else:
        logger.debug("community already exists, updating name..")
        discord_community.community_name = guild_name
        discord_community.save()

        # Store token for the user who (re)installed Discord
        if user_token and user_id:
            # FIXME user id needs to be combined with guild..
            pass
            """
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
            """

        return redirect(f"{redirect_route}?success=true")


# def initiate_action_vote(discord_community, proposal, users=None, template=None, channel=None):
#     message = "This action is governed by the following policy: " + proposal.policy.name
#     if template:
#         message = template

#     # User can input either channel_id or channel_name as channel parameter.
#     # Here, we must check whether the user entered a valid channel_id. If not,
#     # we check if the user entered a valid channel_name.
#     channel_id = None
#     c = DiscordChannel.objects.filter(guild_id=discord_community.team_id, channel_id=channel)
#     if c.exists():
#         channel_id = c[0].channel_id
#     else:
#         c = DiscordChannel.objects.filter(guild_id=discord_community.team_id, channel_name=channel)
#         if c.exists():
#             channel_id = c[0].channel_id
#     if channel_id == None:
#         raise Exception("Failed to determine which channel to post in")

#     res = discord_community.post_message(text=message, channel=channel_id)

#     proposal.community_post = res['id']
#     proposal.save()

#     time.sleep(1)
#     discord_community.make_call(f'channels/{channel_id}/messages/{res["id"]}/reactions/%F0%9F%91%8D/@me', method="PUT")
#     time.sleep(1)
#     discord_community.make_call(f'channels/{channel_id}/messages/{res["id"]}/reactions/%F0%9F%91%8E/@me', method="PUT")
