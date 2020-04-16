from django.shortcuts import render
from django.http import HttpResponse
from policykit.settings import REDDIT_CLIENT_SECRET
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from urllib import parse
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)


# Create your views here.

def oauth(request):
    logger.info(request)
    
    state = request.GET.get('state')
    if state == "policykit_reddit_string":
        
        code = request.GET.get('code')
        
        
        
        data = parse.urlencode({
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'https://policykit.org/reddit/oauth',
            }).encode()
            
        req = urllib.request.Request('https://www.reddit.com/api/v1/access_token', data=data)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        
        logger.info(res)
        
        if res['ok']:
        
        
    
        response = redirect('/login?success=true')
        return response
    
    response = redirect('/login?success=false')
    return response



@csrf_exempt
def action(request):
    json_data = json.loads(request.body)
    logger.info('RECEIVED ACTION')
    logger.info(json_data)
    
