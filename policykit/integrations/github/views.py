import logging

from django.shortcuts import redirect
from integrations.github.models import GithubCommunity
from policyengine.metagov_app import metagov
from policyengine.models import Community

logger = logging.getLogger(__name__)


def github_install(request):
    """
    Gets called after the oauth install flow is completed. This is the redirect_uri that was passed to the oauth flow.
    """
    logger.debug(f"GitHub installation completed: {request.GET}")

    # Metagov identifier for the "parent community" to install GitHub to
    metagov_community_slug = request.GET.get("community")
    # We can only add GitHub to existing communities for now, so redirect to the settings page
    redirect_route = "/main/settings"

    try:
        community = Community.objects.get(metagov_slug=metagov_community_slug)
    except Community.DoesNotExist:
        return redirect(f"{redirect_route}?error=community_not_found")

    if request.GET.get("error"):
        return redirect(f"{redirect_route}?error={request.GET.get('error')}")

    plugin = metagov.get_community(metagov_community_slug).get_plugin("github")
    team_id = plugin.community_platform_id

    github_community = GithubCommunity.objects.filter(team_id=team_id, community=community)

    if github_community.exists():
        logger.debug(f"Github community for installation {team_id} already exists, doing nothing.")
        return redirect(f"{redirect_route}?success=true")

    logger.debug(f"Creating new GithubCommunity under {community}")
    data = plugin.get_installation()
    readable_name = data["account"]["login"]
    target_type = data["target_type"]  # User or Organization

    github_community = GithubCommunity.objects.create(
        community=community,
        community_name=readable_name,
        team_id=team_id,
    )

    return redirect(f"{redirect_route}?success=true")
