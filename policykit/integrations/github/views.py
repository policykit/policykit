import logging
import requests
from django.conf import settings
from django.shortcuts import redirect
from policyengine.models import Community, CommunityRole

logger = logging.getLogger(__name__)


def github_install(request):
    logger.debug(f"GitHub installation completed: {request.GET}")

    # metagov identifier for the "parent community" to install GitHub to
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

    return redirect(f"{redirect_route}?success=true")
