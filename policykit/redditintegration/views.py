from django.shortcuts import render
from django.http import HttpResponse
from policykit.settings import REDDIT_CLIENT_SECRET
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from urllib import parse
import urllib.request
import json
import base64
import logging

logger = logging.getLogger(__name__)


# Create your views here.

def oauth(request):
    logger.info(request)
    
    state = request.GET.get('state')
    if state == "policykit_reddit_string":
        
        code = request.GET.get('code')
        
        logger.info(code)
        
        data = parse.urlencode({
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'https://policykit.org/reddit/oauth',
            }).encode()
            
        req = urllib.request.Request('https://www.reddit.com/api/v1/access_token', data=data)
        
        string = '%s:%s' % ('QrZzzkLgVc1x6w', REDDIT_CLIENT_SECRET)

        base64string = base64.standard_b64encode(string.encode('utf-8'))

        req.add_header("Authorization", "Basic %s" % base64string)
        req.add_header("User-Agent", "PolicyKit-App-Reddit-Integration")

        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        
        logger.info(res)
        
    
        response = redirect('/login?success=true')
        return response
    
    response = redirect('/login?success=false')
    return response



@csrf_exempt
def action(request):
    json_data = json.loads(request.body)
    logger.info('RECEIVED ACTION')
    logger.info(json_data)
    
