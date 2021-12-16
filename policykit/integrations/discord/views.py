import logging
import requests

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from integrations.discord.models import (
    DiscordCommunity,
    DISCORD_SLASH_COMMAND_NAME,
    DISCORD_SLASH_COMMAND_OPTION,
    DISCORD_SLASH_COMMAND_DESCRIPTION,
)
from policyengine.models import Community
from policyengine.utils import render_starterkit_view
from policyengine.metagov_app import metagov

logger = logging.getLogger(__name__)


def discord_login(request):
    """
    This view gets hit after the user has logged in with Discord successfully.
    We need a special view for Discord (rather then the default policyengine 'authenticate_user' view) because we need to look up which of the users Guilds to log into.
    If the user belongs to multiple Guilds that use PolicyKit, redirect them to a screen to select which guild to log in with.
    """
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

    if len(guilds) == 1:
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
        request.session["user_id"] = user_id
        request.session["user_token"] = user_token
        return render(request, "policyadmin/configure_discord.html", {"integrated_guilds": guilds})

    # Note: this is not always an accurate error message.
    return redirect("/login?error=policykit_not_yet_installed_to_that_community")


def login_selected_guild(request):
    """
    This view only gets hit after user completes the configure_discord.html form.
    This only applies for users that have multiple guilds set up with PolicyKit.
    """
    guild_id = request.POST["guild_id"]
    if not guild_id:
        return redirect("/login?error=guild_id_missing")

    user_id = request.session.get("user_id")
    user_token = request.session.get("user_token")
    if not user_token or not user_id:
        return redirect("/login?error=user_info_missing")

    user = authenticate(request, team_id=guild_id, user_id=user_id, user_token=user_token)
    if user:
        login(request, user)
        return redirect("/main")
    else:
        return redirect("/login?error=invalid_login")


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
    logger.debug(f"Found Metagov Plugin {discord_plugin} with guild info: {guild_info}")
    guild_name = guild_info["name"]

    # Register/update the default PolicyKit guild command
    discord_plugin.register_guild_command(
        DISCORD_SLASH_COMMAND_NAME,
        description=DISCORD_SLASH_COMMAND_DESCRIPTION,
        options=[{"name": DISCORD_SLASH_COMMAND_OPTION, "description": "Command", "type": 3, "required": True}],
    )

    discord_community = DiscordCommunity.objects.filter(team_id=guild_id).first()
    if discord_community is None:
        logger.debug(f"Creating new DiscordCommunity for guild '{guild_name}' under {community}")
        discord_community = DiscordCommunity.objects.create(
            community=community,
            community_name=guild_name,
            team_id=guild_id,
        )

        # Get the list of users and create a DiscordUser object for each user
        guild_members = discord_plugin.method(route=f"guilds/{guild_id}/members?limit=1000")
        owner_id = guild_info["owner_id"]
        creator_user = None
        for member in guild_members:
            if member["user"].get("bot"):
                continue

            member_user_id = member["user"]["id"]
            u, _ = discord_community._update_or_create_user(member["user"])

            # If this user is the user that's installing discord, mark them as an admin and store their token
            if user_token and user_id and member_user_id == user_id:
                logger.debug(f"Storing access_token for installing user ({user_id})")
                u.is_community_admin = True
                u.access_token = user_token
                u.save()
                creator_user = u

            # Make guild owner and admin by default
            if member_user_id == owner_id:
                u.is_community_admin = True
                u.save()

        if is_new_community:
            # if this is an entirely new parent community, select starter kit
            return render_starterkit_view(request, discord_community.community.pk, creator_username=creator_user.username if creator_user else None)
        else:
            # discord is being added to an existing community that already has other platforms and starter policies
            return redirect(f"{redirect_route}?success=true")

    else:
        logger.debug("community already exists, updating name..")
        discord_community.community_name = guild_name
        discord_community.save()

        # Store token for the user who (re)installed Discord
        if user_token and user_id:
            installer, created = discord_community._update_or_create_user({"id": user_id})
            installer.is_community_admin = True
            installer.access_token = user_token
            installer.save()

            if created:
                logger.debug(f"Installer user '{user_id}' is a new user, fetching user details...")
                user_data = discord_community.make_call("discord.get_user", {"user_id": user_id})
                discord_community._update_or_create_user(user_data)

        return redirect(f"{redirect_route}?success=true")
