from django.shortcuts import render
from django.http import HttpResponse
from policykit.settings import REDDIT_CLIENT_SECRET
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)


# Create your views here.

def oauth(request):
    logger.info(request)



@csrf_exempt
def action(request):
    json_data = json.loads(request.body)
    logger.info('RECEIVED ACTION')
    logger.info(json_data)
    
