import logging
import json
from django.contrib.auth import get_user
from django.http.response import HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import redirect
import integrations.metagov.api as MetagovAPI
from integrations.opencollective.models import OpencollectiveCommunity

logger = logging.getLogger(__name__)


@login_required(login_url="/login")
@permission_required("metagov.can_edit_metagov_config", raise_exception=True)
@csrf_exempt
def enable_integration(request):
    user = get_user(request)
    community = user.community.community

    config = json.loads(request.body)
    logger.warn(f"Making request to enable OC with config {config}")
    res = MetagovAPI.enable_plugin(community.metagov_slug, "opencollective", config)
    logger.debug(res)
    team_id = res["config"]["collective_slug"]
    # here we could register the webhook_url, if Open Collective supported registering hooks via API call.

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

    return JsonResponse(res, safe=False)


@login_required(login_url="/login")
@permission_required("metagov.can_edit_metagov_config", raise_exception=True)
def disable_integration(request):
    id = int(request.GET.get("id"))
    user = get_user(request)
    community = user.community.community

    oc_community = community.get_platform_community(name="opencollective")
    if not oc_community:
        return redirect("/main/settings?error=no_such_plugin")

    # Validate that this plugin ID is valid for the community that this user is logged into.
    # Important! This prevents the user from disabling plugins for other communities.
    plugin_conf = MetagovAPI.get_plugin_config(community.metagov_slug, "opencollective", id)
    if not plugin_conf:
        return redirect("/main/settings?error=no_such_plugin")

    # Delete the Open Collective plugin in Metagov
    MetagovAPI.delete_plugin(name="opencollective", id=id)

    # TODO: Delete the OpencollectiveCommunity model in PolicyKit?
    # oc_community.delete()

    return redirect("/main/settings")
