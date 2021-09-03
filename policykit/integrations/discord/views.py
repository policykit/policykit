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
    guild_id = request.GET.get("guild_id")
    user = authenticate(request, user_token=user_token, user_id=user_id, team_id=guild_id)
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
    guild_id = request.GET.get("guild_id")

    # Get guild info from Discord
    response = requests.post(
        f"{settings.METAGOV_URL}/api/internal/action/discord.getguild",
        json={"parameters": {"guild_id": guild_id}},
        headers={"X-Metagov-Community": metagov_community_slug},
    )
    if not response.ok:
        return redirect(f"{redirect_route}?error=server_error")
    guild_info = response.json()
    readable_name = guild_info['name']

    # Set readable_name for Community
    if not community.readable_name:
        community.readable_name = readable_name
        community.save()

    user_group, _ = CommunityRole.objects.get_or_create(
        role_name="Base User", name="Discord: " + readable_name + ": Base User"
    )

    discord_community = DiscordCommunity.objects.filter(team_id=guild_id).first()
    if discord_community is None:
        logger.debug(f"Creating new DiscordCommunity under {community}")
        discord_community = DiscordCommunity.objects.create(
            community=community,
            community_name=readable_name,
            team_id=guild_id,
            base_role=user_group,
        )
        user_group.community = discord_community
        user_group.save()

        # Get the list of users and create a DiscordUser object for each user
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

        context = {
            "server_url": SERVER_URL,
            "starterkits": get_starterkits_info(),
            "community_name": discord_community.community_name,
            "creator_token": user_token,
            "platform": "discord",
            # redirect to settings page or login page depending on whether it's a new community
            "redirect": redirect_route
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
"""
