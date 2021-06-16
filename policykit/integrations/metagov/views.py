import json
import logging

from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import ContentType, Permission
from django.contrib.contenttypes.models import ContentType
from django.http import (
    JsonResponse,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseServerError,
    HttpResponseNotFound,
)
from django.views.decorators.csrf import csrf_exempt
from integrations.metagov.models import MetagovProcess, MetagovPlatformAction, MetagovUser
from policyengine.models import Community, CommunityPlatform, CommunityRole
from integrations.slack.models import SlackCommunity
import integrations.metagov.api as MetagovAPI

logger = logging.getLogger(__name__)


@login_required(login_url="/login")
@csrf_exempt
def save_config(request):
    user = get_user(request)
    community = user.community
    data = json.loads(request.body)

    try:
        community_config = MetagovAPI.update_metagov_community(community, data.get("plugins", []))
    except Exception as e:
        return HttpResponseBadRequest(e)

    hooks = MetagovAPI.get_webhooks(community)
    return JsonResponse({"hooks": hooks, "config": community_config})


# INTERNAL ENDPOINT, no auth
@csrf_exempt
def internal_receive_outcome(request, id):
    if request.method != "POST" or not request.body:
        return HttpResponseBadRequest()
    try:
        process = MetagovProcess.objects.get(pk=id)
    except MetagovProcess.DoesNotExist:
        return HttpResponseNotFound()

    try:
        body = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest("unable to decode body")

    logger.info(f"Received external process outcome: {body}")
    process.json_data = json.dumps(body)
    process.save()
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

    if body.get("source") == "slack":
        # Route Slack event to the correct SlackCommunity handler
        slack_community = SlackCommunity.objects.filter(community=community).first()
        if slack_community is None:
            return HttpResponseBadRequest(f"no slack community exists for {metagov_community_slug}")
        slack_community.handle_metagov_event(body)
        return HttpResponse()

    # For all other sources, create generic MetagovPlatformActions.

    platform_community = CommunityPlatform.objects.filter(community=community).first()
    if platform_community is None:
        logger.error(f"No platforms exist for community '{community}'")
        return HttpResponse()

    # Get or create a MetagovUser that's tied to the PlatformCommunity, and give them permission to propose MetagovPlatformActions

    # Hack so MetagovUser username doesn't clash with usernames from other communities (django User requires unique username).
    # TODO(#299): make the CommunityUser model unique on community+username, not just username.
    initiator = body["initiator"]
    prefixed_username = f"{initiator['provider']}.{initiator['user_id']}"
    metagov_user, _ = MetagovUser.objects.get_or_create(
        username=prefixed_username, provider=initiator["provider"], community=platform_community
    )

    # Give this user permission to propose any MetagovPlatformAction
    user_group, usergroup_created = CommunityRole.objects.get_or_create(
        role_name="Base User", name=f"Metagov: {metagov_community_slug}: Base User"
    )
    if usergroup_created:
        user_group.community = platform_community
        content_type = ContentType.objects.get_for_model(MetagovPlatformAction)
        permission, _ = Permission.objects.get_or_create(
            codename="add_metagovaction",
            name="Can add metagov action",
            content_type=content_type,
        )
        user_group.permissions.add(permission)
        user_group.save()
    user_group.user_set.add(metagov_user)

    # Create MetagovPlatformAction
    new_api_action = MetagovPlatformAction()
    new_api_action.community = platform_community
    new_api_action.initiator = metagov_user
    new_api_action.event_type = f"{body['source']}.{body['event_type']}"
    new_api_action.json_data = json.dumps(body["data"])

    # Save to create Proposal and trigger PlatformPolicy evaluations
    new_api_action.save()
    if not new_api_action.pk:
        return HttpResponseServerError()

    logger.info(f"Created new MetagovPlatformAction with pk {new_api_action.pk}")
    return HttpResponse()
