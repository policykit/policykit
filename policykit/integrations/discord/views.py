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
        # FIXME test
        # If user has more than one PK-integrated Discord guild, bring user to screen to select which guild's dashboard to login to
        return render(
            request, "policyadmin/configure_discord.html", {"integrated_guilds": guilds, "access_token": user_token}
        )

    # user = authenticate(request, user_token=user_token, user_id=user_id, team_id=guild_id)
    # if user:
    #     login(request, user)
    #     return redirect("/main")

    # Note: this is not always an accurate error message.
    return redirect("/login?error=policykit_not_yet_installed_to_that_community")


def discord_install(request):
    logger.debug(f"Discord installation completed: {request.GET}")

    # metagov identifier for the "parent community" to install Discord to
    metagov_community_slug = request.GET.get("community")
    community, is_new_community = Community.objects.get_or_create(metagov_slug=metagov_community_slug)

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

    # Fetch guild info to get the guild name
    response = requests.post(
        f"{settings.METAGOV_URL}/api/internal/action/discord.get-guild",
        headers={"X-Metagov-Community": metagov_community_slug},
    )
    if not response.ok:
        return redirect(f"{redirect_route}?error=server_error")
    guild_info = response.json()
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
        # discord_community.community.readable_name = readable_name
        # discord_community.community.save()

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
