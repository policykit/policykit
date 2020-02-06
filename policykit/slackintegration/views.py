from django.shortcuts import render
from django.http import HttpResponse
from urllib import parse
import urllib.request
from policykit.settings import CLIENT_SECRET
from django.contrib.auth import login, authenticate
import logging
from django.shortcuts import redirect
import json
from slackintegration.models import SlackIntegration, SlackUser, SlackRenameConversation, SlackJoinConversation, SlackPostMessage
from django.contrib.auth.models import User, Group
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

# Create your views here.

def oauth(request):
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    data = parse.urlencode({
        'client_id': '455205644210.932801604965',
        'client_secret': CLIENT_SECRET,
        'code': code,
        }).encode()
        
    req = urllib.request.Request('https://slack.com/api/oauth.v2.access', data=data)
    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))
    
    logger.info(res)
    
    if state =="user": 
        user = authenticate(request, oauth=res)
        if user:
            login(request, user)
            
    elif state == "app":
        s = SlackIntegration.objects.filter(team_id=res['team']['id'])
        user_group,_ = Group.objects.get_or_create(name="Slack")
        if not s.exists():
            _ = SlackIntegration.objects.create(
                community_name=res['team']['name'],
                team_id=res['team']['id'],
                access_token=res['access_token'],
                user_group=user_group
                )
        else:
            s[0].community_name = res['team']['name']
            s[0].team_id = res['team']['id']
            s[0].access_token = res['access_token']
            s[0].save()
        
    response = redirect('/')
    return response


@csrf_exempt
def action(request):
    json_data = json.loads(request.body)
    logger.info(json_data)
    
    action_type = json_data.get('type')
    
    if action_type == "url_verification":
        challenge = json_data.get('challenge')
        return HttpResponse(challenge)
    elif action_type == "event_callback":
        event = json_data.get('event')
        team_id = json_data.get('team_id')
        integration = SlackIntegration.objects.get(team_id=team_id)
        author = SlackUser.objects.all()[0] # TODO Change this to admin user? Bot user?
#         author_id = json_data.get('authed_users')[0]

        if event.get('type') == "channel_rename":
            
            new_action = SlackRenameConversation()
            new_action.community_integration = integration
            new_action.author = author
            new_action.name = event['channel']['name']
            new_action.channel = event['channel']['id']
            new_action.save(slack_revert=True)
    
        elif event.get('type') == "member_joined_channel":
            new_action = SlackJoinConversation()
            new_action.community_integration = integration
            inviter_user = event.get('inviter')
            new_action.author = author
            new_action.users = event.get('user')
            new_action.channel = event['channel']
            new_action.save(slack_revert=True, inviter=inviter_user)
    
        elif event.get('type') == 'message':
            new_action = SlackPostMessage()
            new_action.community_integration = integration
            new_action.author = author
            new_action.text = event['text']
            new_action.channel = event['channel']
            time_stamp = event['ts']
            poster = event['user']
            new_action.save(time_stamp=time_stamp, poster=poster)
            
    
    return HttpResponse("")
    
