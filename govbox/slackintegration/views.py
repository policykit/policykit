from django.shortcuts import render
from urllib import parse
import urllib.request
from govbox.settings import CLIENT_SECRET
from django.contrib.auth import login, authenticate
import logging
from django.shortcuts import redirect
import json
from slackintegration.models import SlackIntegration, SlackUser
from django.contrib.auth.models import User, Group

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
        user = authenticate(request, oauth=res)
        if user:
            login(request, user)
            
    elif state == "app":
        s = SlackIntegration.objects.filter(team_id=res['team_id'])
        user_group = Group.objects.create(name="Slack")
        if not s.exists():
            _ = SlackIntegration.objects.create(
                community_name=res['team_name'],
                team_id=res['team_id'],
                access_token=res['access_token'],
                user_group=user_group
                )
        else:
            s[0].community_name = res['team_name']
            s[0].team_id = res['team_id']
            s[0].access_token = res['access_token']
            s[0].save()
        
    response = redirect('/')
    return response
        
    