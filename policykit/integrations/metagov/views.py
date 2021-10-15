import json
import logging

from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import redirect
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
    HttpResponseNotFound,
)
import integrations.metagov.api as MetagovAPI
from django.views.decorators.csrf import csrf_exempt
from integrations.metagov.models import MetagovTrigger, MetagovUser
from policyengine.models import Community, Proposal
from integrations.slack.models import SlackCommunity
from integrations.github.models import GithubCommunity
from integrations.loomio.models import LoomioCommunity
from integrations.opencollective.models import OpencollectiveCommunity

logger = logging.getLogger(__name__)


# INTERNAL ENDPOINT, no auth
@csrf_exempt
def internal_receive_outcome(request, id):
    if request.method != "POST" or not request.body:
        return HttpResponseBadRequest()
    try:
        body = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest("unable to decode body")

    process_name = body["name"]
    logger.info(f"Received {process_name} metagov process update: {body}")

    try:
        proposal = Proposal.objects.get(pk=id)
    except Proposal.DoesNotExist:
        return HttpResponseNotFound()

    # Save the raw data on the Proposal
    proposal.governance_process_json = json.dumps(body)

    # For platforms that support creating BooleanVotes to track votes
    #FIXME use routing instead of this
    if process_name.startswith("slack."):
        community = SlackCommunity.objects.get(community__metagov_slug=body["community"])
        community.handle_metagov_process(proposal, body)
    elif process_name.startswith("github."):
        community = GithubCommunity.objects.get(community__metagov_slug=body["community"])
        community.handle_metagov_process(proposal, body)
    elif process_name.startswith("loomio."):
        community = LoomioCommunity.objects.get(community__metagov_slug=body["community"])
        community.handle_metagov_process(proposal, body)

    proposal.save()
    return HttpResponse()


# INTERNAL ENDPOINT, no auth
@csrf_exempt
def internal_receive_action(request):
    """
    Receive event from Metagov
    """

    if request.method != "POST" or not request.body:
        return HttpResponseBadRequest()
    try:
        body = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest("unable to decode body")
    logger.info(f"Received metagov action: {body}")

    metagov_community_slug = body.get("community")

    try:
        community = Community.objects.get(metagov_slug=metagov_community_slug)
    except Community.DoesNotExist:
        logger.error(f"Received event for community {metagov_community_slug} which doesn't exist in PolicyKit")
        return HttpResponseBadRequest("Community does not exist")

    # Special cases for receiving events from "governable platforms" that have fully featured integrations
    event_platform = body["source"]
    if event_platform == "slack":
        cp = SlackCommunity.objects.filter(community=community).first()
        if cp:
            cp.handle_metagov_event(body)
            return HttpResponse()

    if event_platform == "github":
        cp = GithubCommunity.objects.filter(community=community).first()
        if cp:
            new_action = cp.handle_metagov_event(body)
            if new_action:
                return HttpResponse()

    if event_platform == "opencollective":
        cp = OpencollectiveCommunity.objects.filter(community=community).first()
        if cp:
            new_action = cp.handle_metagov_event(body)
            if new_action:
                return HttpResponse()

    # Create generic MetagovTrigger for the event

    # FIXME: trigger is arbitrarily tied to first platform. Should create a MetagovCommunity and connect generic triggers to it?
    cp = community.get_platform_communities().first()
    if cp is None:
        logger.error(f"No platforms exist for community '{community}'")
        return HttpResponse()

    # Get or create a MetagovUser that's tied to the PlatformCommunity, and give them permission to propose MetagovTriggers

    # Hack so MetagovUser username doesn't clash with usernames from other communities (django User requires unique username).
    # TODO(#299): make the CommunityUser model unique on community+username, not just username.
    initiator = body["initiator"]
    prefixed_username = f"{initiator['provider']}.{initiator['user_id']}"
    metagov_user, _ = MetagovUser.objects.get_or_create(
        username=prefixed_username, readable_name=initiator["user_id"], provider=initiator["provider"], community=cp
    )

    # Create MetagovTrigger
    trigger_action = MetagovTrigger(
        community=cp,
        initiator=metagov_user,
        event_type=f"{body['source']}.{body['event_type']}",
        json_data=json.dumps(body["data"]),
    )
    proposals = trigger_action.evaluate()

    logger.debug(f"trigger_action proposals: {proposals}")
    logger.debug(f"trigger_action saved?: {trigger_action.pk is not None}")
    return HttpResponse()


@login_required(login_url="/login")
@permission_required("metagov.can_edit_metagov_config", raise_exception=True)
@csrf_exempt
def enable_integration(request):
    """
    API Endpoint to enable a Metagov plugin (called on config form submission from JS).
    This is only used for plugins that DON'T have a corresponding PolicyKit integration.
    For platforms with integrations (Open Collective, Github, etc) the installation
    is handled by the integration.
    """
    name = request.GET.get("name")  # name of the plugin
    user = get_user(request)
    community = user.community.community

    assert name is not None
    config = json.loads(request.body)
    logger.debug(f"Making request to enable {name} with config {config} for {community}")
    res = MetagovAPI.enable_plugin(community.metagov_slug, name, config)
    return JsonResponse(res, safe=False)


@login_required(login_url="/login")
@permission_required("metagov.can_edit_metagov_config", raise_exception=True)
@csrf_exempt
def disable_integration(request):
    """
    API Endpoint to disable a Metagov plugin (navigated to from Settings page).
    This is only used for plugins that DON'T have a corresponding PolicyKit integration.
    For platforms with integrations (Open Collective, Github, etc) the installation
    is handled by the integration.
    """
    # name of the plugin
    name = request.GET.get("name")
    # id of the plugin
    id = int(request.GET.get("id"))

    user = get_user(request)
    community = user.community.community

    # Validate that this plugin ID is valid for the community that this user is logged into.
    # Important! This prevents the user from disabling plugins for other communities.
    plugin_conf = MetagovAPI.get_plugin_config(community.metagov_slug, name, id)
    if not plugin_conf:
        return redirect("/main/settings?error=no_such_plugin")

    logger.debug(f"Deleting plugin {name} {id} for community {community}")
    MetagovAPI.delete_plugin(name=name, id=id)

    return redirect("/main/settings")