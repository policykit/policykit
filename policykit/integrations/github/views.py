import logging
import requests
from django.conf import settings
from django.shortcuts import redirect
from policyengine.models import Community

logger = logging.getLogger(__name__)


def github_install(request):
    logger.debug(f"GitHub installation completed: {request.GET}")

    # metagov identifier for the "parent community" to install GitHub to
    metagov_community_slug = request.GET.get("community")
    # we can only add GitHub to existing communities for now, so redirect to the settings page
    redirect_route = "/main/settings"

    try:
        Community.objects.get(metagov_slug=metagov_community_slug)
    except Community.DoesNotExist:
        return redirect(f"{redirect_route}?error=community_not_found")

    # validate state
    expected_state = request.session.get("community_install_state")
    if expected_state is None or request.GET.get("state") is None or (not request.GET.get("state") == expected_state):
        logger.error(f"expected {expected_state}")
        return redirect(f"{redirect_route}?error=bad_state")

    if request.GET.get("error"):
        return redirect(f"{redirect_route}?error={request.GET.get('error')}")

    return redirect(f"{redirect_route}?success=true")
