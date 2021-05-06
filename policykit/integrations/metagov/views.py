import json
import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import ContentType, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from integrations.metagov.library import metagov_slug, update_metagov_community
from integrations.metagov.models import MetagovProcess, MetagovPlatformAction, MetagovUser
from policyengine.models import Community, CommunityRole

logger = logging.getLogger(__name__)


@csrf_exempt
def save_config(request):
    user = get_user(request)
    community = user.community
    data = json.loads(request.body)

    if data.get("name") != metagov_slug(community):
        return HttpResponseBadRequest("Changing the name is not permitted")
    if data.get("readable_name") != community.community_name:
        return HttpResponseBadRequest("Changing the readable_name is not permitted")

    logger.info(data.get("plugins"))
    try:
        update_metagov_community(community, data.get("plugins", []))
    except Exception as e:
        return HttpResponseBadRequest(e)

    return HttpResponse()


@csrf_exempt
def post_outcome(request, id):
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


@csrf_exempt
def action(request):
    """
    Receive event from Metagov, and create a new MetagovPlatformAction.

    1) Find the `Community` that this metagov community corresponds to (e.g. the SlackCommunity that was configured to use Metagov.)
    2) Get or create a MetagovUser that' stied to the original community (the SlackCommunity)
    3) Give the user permission to propose MetagovPlatformActions
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
        community = Community.objects.get_by_metagov_name(name=metagov_community_slug)
    except Community.DoesNotExist:
        logger.error(f"Received event for community {metagov_community_slug} which doesn't exist in PolicyKit")
        return HttpResponseBadRequest("Community does not exist")

    # Hack so MetagovUser username doesn't clash with usernames from other communities (django User requires unique username).
    # TODO(#299): make the CommunityUser model unique on community+username, not just username.
    initiator = body["initiator"]
    prefixed_username = f"{initiator['provider']}.{initiator['user_id']}"
    metagov_user, _ = MetagovUser.objects.get_or_create(
        username=prefixed_username, provider=initiator["provider"], community=community
    )

    # Give this user permission to propose any MetagovPlatformAction
    user_group, usergroup_created = CommunityRole.objects.get_or_create(
        role_name="Base User", name=f"Metagov: {metagov_community_slug}: Base User"
    )
    if usergroup_created:
        user_group.community = community
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
    new_api_action.community = community
    new_api_action.initiator = metagov_user
    new_api_action.event_type = f"{body['source']}.{body['event_type']}"
    new_api_action.json_data = json.dumps(body["data"])

    # Save to create Proposal and trigger PlatformPolicy evaluations
    new_api_action.save()
    if not new_api_action.pk:
        return HttpResponseServerError()

    logger.info(f"Created new MetagovPlatformAction with pk {new_api_action.pk}")
    return HttpResponse()
