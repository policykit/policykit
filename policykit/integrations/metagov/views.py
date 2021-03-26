import json
import logging

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from integrations.metagov.models import ExternalProcess

logger = logging.getLogger(__name__)

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
