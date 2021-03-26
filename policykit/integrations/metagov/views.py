import json
import logging

import requests
from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from integrations.metagov.library import metagov_slug, update_metagov_community
from integrations.metagov.models import ExternalProcess
from policyengine.models import Community

logger = logging.getLogger(__name__)


@login_required(login_url='/login')
def config_editor(request):
    user = get_user(request)
    if not user.is_community_admin:
        raise PermissionDenied

    community = user.community
    url = f"{settings.METAGOV_URL}/api/internal/community/{metagov_slug(community)}"
    response = requests.get(url)
    if not response.ok:
        if response.status_code == 404:
            logger.info(
                f"No metagov community for {community.community_name}, creating for the first time")
            config = update_metagov_community(community)
        else:
            raise Exception(response.text)
    else:
        config = response.json()

    pretty_config = json.dumps(config, indent=4, separators=(',', ': '))
    return render(request, 'config.html', {'config': pretty_config})


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
    if request.method != 'POST' or not request.body:
        return HttpResponseBadRequest()
    try:
        process = ExternalProcess.objects.get(pk=id)
    except ExternalProcess.DoesNotExist:
        return HttpResponseNotFound()

    try:
        body = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest("unable to decode body")

    logger.info(f"Received external process outcome: {body}")
    if body.get("status") != "completed":
        return HttpResponseBadRequest("process not completed")
    if not body.get('outcome') and not body.get('errors'):
        return HttpResponseBadRequest("completed process must have either outcome or errors")

    process.json_data = json.dumps(body)
    process.save()
    return HttpResponse()


@csrf_exempt
def action(request):
    if request.method != 'POST' or not request.body:
        return HttpResponseBadRequest()
    try:
        body = json.loads(request.body)
    except ValueError:
        return HttpResponseBadRequest("unable to decode body")
    logger.info(f"Received external action: {body}")
    # TODO create ExternalPlatformAction
    return HttpResponse()
