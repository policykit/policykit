import logging
import requests
from django.conf import settings
from django.shortcuts import redirect
from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required, permission_required
from policyengine.models import Community
from integrations.github.models import GithubCommunity
import integrations.metagov.api as MetagovAPI

logger = logging.getLogger(__name__)


def github_install(request):
    logger.debug(f"GitHub installation completed: {request.GET}")

    # Metagov identifier for the "parent community" to install GitHub to
    metagov_community_slug = request.GET.get("community")
    # We can only add GitHub to existing communities for now, so redirect to the settings page
    redirect_route = "/main/settings"

    try:
        community = Community.objects.get(metagov_slug=metagov_community_slug)
    except Community.DoesNotExist:
        return redirect(f"{redirect_route}?error=community_not_found")

    # Validate state
    expected_state = request.session.get("community_install_state")
    if expected_state is None or request.GET.get("state") is None or (not request.GET.get("state") == expected_state):
        logger.error(f"expected {expected_state}")
        return redirect(f"{redirect_route}?error=bad_state")

    if request.GET.get("error"):
        return redirect(f"{redirect_route}?error={request.GET.get('error')}")

    # Get team info from GitHub
    response = requests.post(
        f"{settings.METAGOV_URL}/api/internal/action/github.get-installation",
        headers={"X-Metagov-Community": metagov_community_slug},
    )
    if not response.ok:
        logger.error(f"{response.status_code} {response.text}")
        return redirect(f"{redirect_route}?error=server_error")
    data = response.json()
    logger.debug(data)
    team_id = data["id"]
    readable_name = team_id  # data["account"]["login"]
    target_type = data["target_type"]  # User or Organization

    github_community = GithubCommunity.objects.filter(team_id=team_id, community=community)

    if github_community.exists():
        logger.debug(f"Github community for installation {team_id} already exists, doing nothing.")
        return redirect(f"{redirect_route}?success=true")

    logger.debug(f"Creating new GithubCommunity under {community}")

    github_community = GithubCommunity.objects.create(
        community=community,
        community_name=readable_name,
        team_id=team_id,
    )

    return redirect(f"{redirect_route}?success=true")


@login_required(login_url="/login")
@permission_required("metagov.can_edit_metagov_config", raise_exception=True)
def disable_integration(request):
    id = int(request.GET.get("id"))
    user = get_user(request)
    community = user.community.community

    github_community = community.get_platform_community(name="github")
    if not github_community:
        return redirect("/main/settings?error=no_such_plugin")

    # Validate that this plugin ID is valid for the community that this user is logged into.
    # Important! This prevents the user from disabling plugins for other communities.
    plugin_conf = MetagovAPI.get_plugin_config(community.metagov_slug, "github", id)
    if not plugin_conf:
        return redirect("/main/settings?error=no_such_plugin")

    # Delete the plugin in Metagov
    MetagovAPI.delete_plugin(name="github", id=id)

    # TODO: Delete the community model in PolicyKit?
    # github_community.delete()

    return redirect("/main/settings")
