import logging
import requests
from django.conf import settings
from django.shortcuts import redirect
from policyengine.models import Community, CommunityRole
from integrations.github.models import GithubCommunity

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

    logger.debug(f"Creating new SlackCommunity under {community}")
    user_group, _ = CommunityRole.objects.get_or_create(
        role_name="Base User", name="Github: " + readable_name + ": Base User"
    )
    slack_community = GithubCommunity.objects.create(
        community=community,
        community_name=readable_name,
        team_id=team_id,
        base_role=user_group,
    )
    user_group.community = slack_community
    user_group.save()

    # starterkit for github...?

    return redirect(f"{redirect_route}?success=true")
