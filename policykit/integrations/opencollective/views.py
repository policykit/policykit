import logging
import json
from django.contrib.auth import get_user
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import redirect
from policyengine.metagov_app import metagov
from integrations.opencollective.models import OpencollectiveCommunity

logger = logging.getLogger(__name__)


@login_required(login_url="/login")
@permission_required("constitution.can_add_integration", raise_exception=True)
@csrf_exempt
def enable_integration(request):
    user = get_user(request)
    community = user.community.community
    config = json.loads(request.body)

    mg_community = metagov.get_community(community.metagov_slug)
    plugin = mg_community.enable_plugin("opencollective", config)
    
    # here we could register the webhook_url, if Open Collective supported registering hooks via API call.

    team_id = plugin.community_platform_id
    opencollective_community = OpencollectiveCommunity.objects.filter(team_id=team_id, community=community)

    if opencollective_community.exists():
        logger.debug(f"Opencollective community for installation '{team_id}' already exists, doing nothing.")
    else:
        logger.debug(f"Creating new OpencollectiveCommunity for {team_id} under {community}")
        opencollective_community = OpencollectiveCommunity.objects.create(
            community=community,
            community_name=team_id,
            team_id=team_id,
        )

    return HttpResponse()


@login_required(login_url="/login")
@permission_required("constitution.can_remove_integration", raise_exception=True)
def disable_integration(request):
    id = int(request.GET.get("id"))
    user = get_user(request)
    community = user.community.community

    oc_community = community.get_platform_community(name="opencollective")
    if not oc_community:
        return redirect("/main/settings?error=no_such_plugin")


    mg_community = metagov.get_community(community.metagov_slug)
    mg_community.disable_plugin("opencollective", id=id)

    # TODO: Delete the OpencollectiveCommunity model in PolicyKit?
    # oc_community.delete()

    return redirect("/main/settings")
