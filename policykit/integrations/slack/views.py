import logging
from django.conf import settings
from django.shortcuts import redirect, render
from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required, permission_required
from integrations.slack.models import SlackCommunity, SlackUser
from integrations.slack.utils import get_slack_user_fields
from policyengine.models import Community
from policyengine.utils import get_starterkits_info
from policyengine.metagov_app import metagov

logger = logging.getLogger(__name__)


def slack_install(request):
    """
    Gets called after the oauth install flow is completed. This is the redirect_uri that was passed to the oauth flow.
    """
    logger.debug(f"Slack installation completed: {request.GET}")

    # metagov identifier for the "parent community" to install Slack to
    metagov_community_slug = request.GET.get("community")
    community, is_new_community = Community.objects.get_or_create(metagov_slug=metagov_community_slug)

    # if we're adding slack to an existing community, redirect to the settings page
    redirect_route = "/login" if is_new_community else "/main/settings"

    if request.GET.get("error"):
        return redirect(f"{redirect_route}?error={request.GET.get('error')}")

    # TODO(issue): stop passing user id and token
    user_id = request.GET.get("user_id")
    user_token = request.GET.get("user_token")
    team_id = request.GET.get("team_id")

    mg_community = metagov.get_community(community.metagov_slug)

    # TODO: catch Plugin.DoesNotExist
    slack_plugin = mg_community.get_plugin("slack", team_id)
    team_info = slack_plugin.method(method_name="team.info")
    team = team_info["team"]
    team_id = team["id"]
    readable_name = team["name"]

    slack_community = SlackCommunity.objects.filter(team_id=team_id).first()
    if slack_community is None:
        logger.debug(f"Creating new SlackCommunity under {community}")
        slack_community = SlackCommunity.objects.create(
            community=community, community_name=readable_name, team_id=team_id
        )

        # get the list of users, create SlackUser object for each user
        logger.debug(f"Fetching user list for {slack_community}...")
        # from policyengine.models import LogAPICall

        response = slack_plugin.method(method_name="users.list")

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

        if is_new_community:
            context = {
                "server_url": settings.SERVER_URL,
                "starterkits": get_starterkits_info(),
                "community_id": slack_community.community.pk,
                "creator_token": user_token,
            }
            return render(request, "policyadmin/init_starterkit.html", context)
        else:
            return redirect(f"{redirect_route}?success=true")

    else:
        logger.debug("community already exists, updating name..")
        slack_community.community_name = readable_name
        slack_community.save()

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


@login_required
@permission_required("constitution.can_remove_integration", raise_exception=True)
def disable_integration(request):
    id = int(request.GET.get("id"))
    user = get_user(request)
    community = user.community.community

    # FIXME: implement support for disabling the slack plugin. We should show a warning, as this may
    # include deleting the SlackCommunity, uninstalling the Slack app, etc.
    return redirect("/main/settings?error=cant_delete_slack")
