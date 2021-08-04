import logging
import requests
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from integrations.slack.models import SlackCommunity, SlackUser, SLACK_METHOD_ACTION
from integrations.slack.utils import get_slack_user_fields
from policyengine.models import Community, CommunityRole
from policyengine.utils import get_starterkits_info

logger = logging.getLogger(__name__)


def slack_login(request):
    """redirect after metagov has gotten the slack user token"""
    logger.debug(f"slack_login: {request.GET}")

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


def slack_install(request):
    logger.debug(f"Slack installation completed: {request.GET}")

    # metagov identifier for the "parent community" to install Slack to
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

    # Get team info from Slack
    response = requests.post(
        f"{settings.METAGOV_URL}/api/internal/action/slack.method",
        json={"parameters": {"method_name": "team.info"}},
        headers={"X-Metagov-Community": metagov_community_slug},
    )
    if not response.ok:
        return redirect(f"{redirect_route}?error=server_error")
    data = response.json()
    team = data["team"]
    team_id = team["id"]
    readable_name = team["name"]

    # Set readable_name for Community
    if not community.readable_name:
        community.readable_name = readable_name
        community.save()

    user_group, _ = CommunityRole.objects.get_or_create(
        role_name="Base User", name="Slack: " + readable_name + ": Base User"
    )

    slack_community = SlackCommunity.objects.filter(team_id=team_id).first()
    if slack_community is None:
        logger.debug(f"Creating new SlackCommunity under {community}")
        slack_community = SlackCommunity.objects.create(
            community=community,
            community_name=readable_name,
            team_id=team_id,
            base_role=user_group,
        )
        user_group.community = slack_community
        user_group.save()

        # get the list of users, create SlackUser object for each user
        logger.debug(f"Fetching user list for {slack_community}...")
        from policyengine.models import LogAPICall

        response = LogAPICall.make_api_call(slack_community, {"method_name": "users.list"}, SLACK_METHOD_ACTION)
        for new_user in response["members"]:
            if (not new_user["deleted"]) and (not new_user["is_bot"]) and (new_user["id"] != "USLACKBOT"):
                u, _ = SlackUser.objects.get_or_create(
                    username=new_user["id"],
                    readable_name=new_user["real_name"],
                    avatar=new_user["profile"]["image_24"],
                    community=slack_community,
                )
                if user_token and user_id and new_user["id"] == user_id:
                    logger.debug(f"Storing access_token for installing user ({user_id})")
                    # Installer has is_community_admin because they are an admin in Slack, AND we requested special user scopes from them
                    u.is_community_admin = True
                    u.access_token = user_token
                    u.save()

        context = {
            "server_url": SERVER_URL,
            "starterkits": get_starterkits_info(),
            "community_name": slack_community.community_name,
            "creator_token": user_token,
            "platform": "slack",
            # redirect to settings page or login page depending on whether it's a new community
            "redirect": redirect_route
        }
        return render(request, "policyadmin/init_starterkit.html", context)

    else:
        logger.debug("community already exists, updating name..")
        slack_community.community_name = readable_name
        slack_community.save()
        slack_community.community.readable_name = readable_name
        slack_community.community.save()

        # Store token for the user who (re)installed Slack
        if user_token and user_id:
            installer = SlackUser.objects.filter(community=slack_community, username=user_id).first()
            if installer is not None:
                logger.debug(f"Storing access_token for installing user ({user_id})")
                # Installer has is_community_admin because they are an admin in Slack, AND we requested special user scopes from them
                installer.is_community_admin = True
                installer.access_token = user_token
                installer.save()
            else:
                logger.debug(f"User '{user_id}' is re-installing but no SlackUser exists for them, creating one..")
                response = slack_community.make_call("slack.method", {"method_name": "users.info", "user": user_id})
                user_info = response["user"]
                user_fields = get_slack_user_fields(user_info)
                user_fields["is_community_admin"] = True
                user_fields["access_token"] = user_token
                SlackUser.objects.update_or_create(
                    community=slack_community,
                    username=user_info["id"],
                    defaults=user_fields,
                )

        return redirect(f"{redirect_route}?success=true")
