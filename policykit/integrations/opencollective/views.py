import logging
import urllib

from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required, permission_required

from django.shortcuts import redirect
from integrations.opencollective.models import (
    OpencollectiveCommunity,
)
from policyengine.models import Community
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
        params = urllib.parse.urlencode({
            'error': request.GET.get("error"),
            'error_description': request.GET.get('error_description')
        })
        return redirect(f"{redirect_route}?{params}")

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

        # if is_new_community:
        #     # if this is an entirely new parent community, select starter kit
        #     return render_starterkit_view(
        #         request, oc_community.community.pk, creator_username=creator_user.username if creator_user else None
        #     )
        # else:
        # discord is being added to an existing community that already has other platforms and starter policies
        return redirect(f"{redirect_route}?success=true")

    else:
        logger.debug("OC community already exists")
        return redirect(f"{redirect_route}?success=true")



@login_required
@permission_required("constitution.can_remove_integration", raise_exception=True)
def disable_integration_without_deletion(request):
    """
    Disable OpenCollective integration 
    without deleting the OpencollectiveCommunity object
    so we can re-add integration and get a fresh
    OAuth token.
    """
    integration = "opencollective"
    id = int(request.GET.get("id")) # id of the plugin
    user = get_user(request)
    community = user.community.community
    logger.debug(f"Disabling plugin {integration} {id} for community {community}")

    # Disable the Metagov Plugin
    metagov.get_community(community.metagov_slug).disable_plugin(integration, id=id)

    # Unlike the generic disable_integration function, 
    # we don't delete the platform community here

    return redirect("/main/settings")