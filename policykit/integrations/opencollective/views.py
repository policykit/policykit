import logging
import requests

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from integrations.opencollective.models import (
    OpencollectiveCommunity,
)
from policyengine.models import Community
from policyengine.utils import render_starterkit_view
from policyengine.metagov_app import metagov

logger = logging.getLogger(__name__)


def opencollective_install(request):
    """
    Gets called after the oauth install flow is completed. This is the redirect_uri that was passed to the oauth flow.
    """
    logger.debug(f"Open Collective installation completed: {request.GET}")

    # metagov identifier for the "parent community" to install Discord to
    metagov_community_slug = request.GET.get("community")
    collective = request.GET.get("collective")
    community, is_new_community = Community.objects.get_or_create(metagov_slug=metagov_community_slug)

    # if we're enabling an integration for an existing community, so redirect to the settings page
    redirect_route = "/login" if is_new_community else "/main/settings"

    if request.GET.get("error"):
        return redirect(f"{redirect_route}?error={request.GET.get('error')}")

    mg_community = metagov.get_community(community.metagov_slug)
    oc_plugin = mg_community.get_plugin("opencollective", collective)
    logger.debug(f"Found Metagov Plugin {oc_plugin}")

    oc_community = OpencollectiveCommunity.objects.filter(team_id=collective).first()
    if oc_community is None:
        logger.debug(f"Creating new OpencollectiveCommunity for collective '{collective}' under {community}")
        oc_community = OpencollectiveCommunity.objects.create(
            community=community,
            community_name=collective,
            team_id=collective,
        )

        if is_new_community:
            # if this is an entirely new parent community, select starter kit
            return render_starterkit_view(
                request, oc_community.community.pk, creator_username=creator_user.username if creator_user else None
            )
        else:
            # discord is being added to an existing community that already has other platforms and starter policies
            return redirect(f"{redirect_route}?success=true")

    else:
        logger.debug("OC community already exists")
        return redirect(f"{redirect_route}?success=true")
