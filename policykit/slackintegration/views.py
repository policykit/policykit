from django.shortcuts import render
from django.http import HttpResponse
from urllib import parse
import urllib.request
from policykit.settings import CLIENT_SECRET
from django.contrib.auth import login, authenticate
import logging
from django.shortcuts import redirect
import json
from slackintegration.models import SlackIntegration, SlackUser, SlackRenameConversation, SlackJoinConversation, SlackPostMessage, SlackPinMessage
from policyengine.models import CommunityAction, UserVote, CommunityAPI, CommunityPolicy, Proposal, LogAPICall
from policyengine.views import check_filter_code, check_policy_code
from django.contrib.auth.models import User, Group
from django.views.decorators.csrf import csrf_exempt
import datetime

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
    
    if res['ok']:
        if state =="user": 
            user = authenticate(request, oauth=res)
            if user:
                login(request, user)
                
        elif state == "app":
            s = SlackIntegration.objects.filter(team_id=res['team']['id'])
            integration = None
            user_group,_ = Group.objects.get_or_create(name="Slack")
            if not s.exists():
                integration = SlackIntegration.objects.create(
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
                integration = s[0]
            
            user = SlackUser.objects.filter(user_id=res['authed_user']['id'])
            if not user.exists():
                
                # CHECK HERE THAT USER IS ADMIN
                
                _ = SlackUser.objects.create(user_id=res['authed_user']['id'],
                                             access_token=res['authed_user']['access_token'],
                                             is_community_admin=True,
                                             community_integration=integration
                                             )
    else:
        # error message stating that the sign-in/add-to-slack didn't work
        response = redirect('/login?error=cancel')
        return response
        
    response = redirect('/login?success=true')
    return response


@csrf_exempt
def action(request):
    json_data = json.loads(request.body)
    logger.info('RECEIVED ACTION')
    logger.info(json_data)
    action_type = json_data.get('type')
    
    if action_type == "url_verification":
        challenge = json_data.get('challenge')
        return HttpResponse(challenge)
    
    elif action_type == "event_callback":
        event = json_data.get('event')
        team_id = json_data.get('team_id')
        integration = SlackIntegration.objects.get(team_id=team_id)
        admin_user = SlackUser.objects.filter(is_community_admin=True)[0]
        current_time_minus = datetime.datetime.now() - datetime.timedelta(seconds=2)

        new_action = None
        policy_kit_action = False
        
        if event.get('type') == "channel_rename":
            
            logs = LogAPICall.objects.filter(proposal_time__gte=current_time_minus,
                                            call_type=integration.API + SlackRenameConversation.ACTION)
            
            if logs.exists():
                for log in logs:
                    j_info = json.loads(log.extra_info)
                    if event['channel']['name'] == j_info['channel']:
                        policy_kit_action = True
            
            if not policy_kit_action:
                new_action = SlackRenameConversation()
                new_action.community_integration = integration
                new_action.initiator = admin_user
                new_action.name = event['channel']['name']
                new_action.channel = event['channel']['id']
                
                prev_names = new_action.get_channel_info()
                new_action.prev_name = prev_names[0]
            
            
        elif event.get('type') == "member_joined_channel":
            new_action = SlackJoinConversation()
            new_action.community_integration = integration
            new_action.inviter_user = event.get('inviter')
            new_action.initiator = admin_user
            new_action.users = event.get('user')
            new_action.channel = event['channel']
        elif event.get('type') == 'message' and event.get('subtype') == None:
            
            logs = LogAPICall.objects.filter(proposal_time__gte=current_time_minus,
                                            call_type=integration.API + SlackPostMessage.ACTION)
            
            if logs.exists():
                for log in logs:
                    j_info = json.loads(log.extra_info)
                    if event['text'] == j_info['text']:
                        policy_kit_action = True
            
            if not policy_kit_action:
                new_action = SlackPostMessage()
                new_action.community_integration = integration
                new_action.text = event['text']
                new_action.channel = event['channel']
                new_action.time_stamp = event['ts']
                
                user = SlackUser.objects.filter(user_id=event['user'], community_integration=integration)
                if user.exists():
                    new_action.initiator = user[0]
                else:
                    user = SlackUser.objects.create(user_id=event['user'], 
                                                    community_integration=integration)
                    new_action.initiator = user
                    
                
                
        elif event.get('type') == 'pin_added':
            new_action = SlackPinMessage()
            new_action.community_integration = integration
            new_action.initiator = admin_user
            new_action.channel = event['channel_id']
            new_action.timestamp = event['item']['message']['ts']
            new_action.user = event['user']
        
        if new_action and not policy_kit_action:
            for policy in CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=new_action.community_integration):
                if check_filter_code(policy, new_action):
                    if not new_action.pk:
                        new_action.community_origin = True
                        new_action.save()
                    # init() goees here
                    cond_result = check_policy_code(policy, new_action.communityaction)
                    if cond_result == Proposal.PROPOSED or cond_result == Proposal.FAILED:
                        new_action.revert()
                        new_action.post_policy()
                    
                    
                    
        
        
        if event.get('type') == 'reaction_added':
            ts = event['item']['ts']
            api_action = CommunityAPI.objects.filter(community_post=ts)
            if api_action:
                api_action = api_action[0]
                action = CommunityAction.objects.filter(api_action=api_action.id)
                if action:
                    action = action[0]
                    if event['reaction'] == '+1' or event['reaction'] == '-1':
                        if event['reaction'] == '+1':
                            value = True
                        elif event['reaction'] == '-1':
                            value = False
                        
                        user = SlackUser.objects.get(user_id=event['user'])
                        uv, created = UserVote.objects.get_or_create(proposal=action.proposal,
                                                                     user=user)
                        uv.boolean_value = value
                        uv.save()
    
    return HttpResponse("")
    
