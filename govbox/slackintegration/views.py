from django.shortcuts import render
from urllib import parse
import urllib.request
from govbox.settings import CLIENT_SECRET
import logging
from django.shortcuts import redirect
import json
from slackintegration.models import SlackIntegration, UserSignIn

logger = logging.getLogger(__name__)

# Create your views here.

def oauth(request):
    
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    data = parse.urlencode({
        'client_id': '455205644210.869594358164',
        'client_secret': CLIENT_SECRET,
        'code': code,
        }).encode()
        
    req = urllib.request.Request('https://slack.com/api/oauth.access', data=data)
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))
    
    if state =="user":
        if not UserSignIn.objects.filter(access_token=res['access_token']).exists():
            s = SlackIntegration.objects.filter(team_id=res['team_id'])
            
            if s.exists():
                u = UserSignIn.objects.create(
                    slack_team = s[0],
                    access_token=res['access_token']
                    )
                
    elif state == "app":
    
        if not SlackIntegration.objects.filter(access_token=res['access_token']).exists():
            s = SlackIntegration.objects.create(
                team_name=res['team_name'],
                team_id=res['team_id'],
                access_token=res['access_token']
                )
        
    response = redirect('/')
    return response
    
    