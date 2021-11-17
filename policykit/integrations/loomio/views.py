import logging
import json
from django.contrib.auth import get_user
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponse
from django.shortcuts import redirect
from policyengine.metagov_app import metagov
from integrations.loomio.models import LoomioCommunity

logger = logging.getLogger(__name__)


@login_required(login_url="/login")
@permission_required("constitution.can_add_integration", raise_exception=True)
@csrf_exempt
def enable_integration(request):
    user = get_user(request)
    community = user.community.community

    config = json.loads(request.body)
    logger.warn(f"Enabling Loomio with config {config}")
    mg_community = metagov.get_community(community.metagov_slug)
    loomio_plugin = mg_community.enable_plugin("loomio", config)
    logger.debug(loomio_plugin)
    team_id = loomio_plugin.community_platform_id
    # here we could register the webhook_url, if Loomio supported registering hooks via API call.

    loomio_community = LoomioCommunity.objects.filter(team_id=team_id, community=community)

    if loomio_community.exists():
        logger.debug(f"Loomio community for installation '{team_id}' already exists, doing nothing.")
    else:
        logger.debug(f"Creating new LoomioCommunity for {team_id} under {community}")
        loomio_community = LoomioCommunity.objects.create(
            community=community,
            team_id=team_id,
        )

    return HttpResponse()


@login_required(login_url="/login")
@permission_required("constitution.can_remove_integration", raise_exception=True)
def disable_integration(request):
    id = int(request.GET.get("id"))
    user = get_user(request)
    community = user.community.community

    loomio_community = community.get_platform_community(name="loomio")
    if not loomio_community:
        return redirect("/main/settings?error=no_such_plugin")

    mg_community = metagov.get_community(community.metagov_slug)
    mg_community.disable_plugin("loomio", id=id)

    # TODO: Delete the LoomioCommunity model in PolicyKit?
    # loomio_community.delete()

    return redirect("/main/settings")
