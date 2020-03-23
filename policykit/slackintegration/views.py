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
from policyengine.models import CommunityAction, BooleanVote, NumberVote, CommunityRole, CommunityAPI, CommunityPolicy, Proposal, LogAPICall, BaseAction, CommunityActionBundle
from policyengine.views import check_filter_code, check_policy_code, initialize_code
from django.contrib.auth.models import User, Group
from django.views.decorators.csrf import csrf_exempt
import datetime

logger = logging.getLogger(__name__)

NUMBERS_TEXT = {'zero': 0,
                'one': 1,
                'two': 2,
                'three': 3,
                'four': 4,
                'five': 5,
                'six': 6,
                'seven': 7,
                'eight': 8,
                'nine': 9
                }


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
            user_group,_ = CommunityRole.objects.get_or_create(name=res['team']['name'])
            if not s.exists():
                integration = SlackIntegration.objects.create(
                    community_name=res['team']['name'],
                    team_id=res['team']['id'],
                    access_token=res['access_token'],
                    base_role=user_group
                    )
            else:
                s[0].community_name = res['team']['name']
                s[0].team_id = res['team']['id']
                s[0].access_token = res['access_token']
                s[0].save()
                integration = s[0]
            
            user = SlackUser.objects.filter(username=res['authed_user']['id'])
            if not user.exists():
                
                # CHECK HERE THAT USER IS ADMIN
                
                _ = SlackUser.objects.create(username=res['authed_user']['id'],
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


def is_policykit_action(integration, test_a, test_b, api_name):
    current_time_minus = datetime.datetime.now() - datetime.timedelta(seconds=2)
    logs = LogAPICall.objects.filter(proposal_time__gte=current_time_minus,
                                            call_type=integration.API + api_name)

    if logs.exists():
        for log in logs:
            j_info = json.loads(log.extra_info)
            if test_a == j_info[test_b]:
                return True
    
    return False


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

        new_api_action = None
        policy_kit_action = False
        
        if event.get('type') == "channel_rename":
            if not is_policykit_action(integration, event['channel']['name'], 'name', SlackRenameConversation.ACTION):
                new_api_action = SlackRenameConversation()
                new_api_action.community_integration = integration
                new_api_action.name = event['channel']['name']
                new_api_action.channel = event['channel']['id']
                u,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                      community_integration=integration)
                new_api_action.initiator = u
                prev_names = new_api_action.get_channel_info()
                new_api_action.prev_name = prev_names[0]
                
        elif event.get('type') == 'message' and event.get('subtype') == None:
            if not is_policykit_action(integration, event['text'], 'text', SlackPostMessage.ACTION):            
                new_api_action = SlackPostMessage()
                new_api_action.community_integration = integration
                new_api_action.text = event['text']
                new_api_action.channel = event['channel']
                new_api_action.time_stamp = event['ts']
                u,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                                           community_integration=integration)
                new_api_action.initiator = u

        elif event.get('type') == "member_joined_channel":
            if not is_policykit_action(integration, event['channel'], 'channel', SlackJoinConversation.ACTION):
                new_api_action = SlackJoinConversation()
                new_api_action.community_integration = integration
                if event.get('inviter'):
                    u,_ = SlackUser.objects.get_or_create(username=event['inviter'],
                                                          community_integration=integration)
                    new_api_action.initiator = u
                else:
                    u,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                          community_integration=integration)
                    new_api_action.initiator = u
                new_api_action.users = event.get('user')
                new_api_action.channel = event['channel']

                
        elif event.get('type') == 'pin_added':
            if not is_policykit_action(integration, event['channel_id'], 'channel', SlackPinMessage.ACTION):
                new_api_action = SlackPinMessage()
                new_api_action.community_integration = integration
                u,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                      community_integration=integration)
                new_api_action.initiator = u
                new_api_action.channel = event['channel_id']
                new_api_action.timestamp = event['item']['message']['ts']


        if new_api_action and not policy_kit_action:
            for policy in CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=new_api_action.community_integration):
                action = CommunityAction()
                action.api_action = new_api_action
                if check_filter_code(policy, action):
                    if not new_api_action.pk:
                        new_api_action.community_origin = True
                        new_api_action.is_bundled = False
                        new_api_action.save()
                    initialize_code(policy, new_api_action.communityaction)
                    cond_result = check_policy_code(policy, new_api_action.communityaction)
                    if cond_result == Proposal.PROPOSED or cond_result == Proposal.FAILED:
                        new_api_action.revert()
                    
                    
                    
        
        
        if event.get('type') == 'reaction_added':
            ts = event['item']['ts']
            action = None
            action_res = CommunityAction.objects.filter(community_post=ts)
            if action_res.exists():
                action = action_res[0]
            
                if event['reaction'] == '+1' or event['reaction'] == '-1':
                    if event['reaction'] == '+1':
                        value = True
                    elif event['reaction'] == '-1':
                        value = False
                    
                    user,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                           community_integration=action.community_integration)
                    uv = BooleanVote.objects.filter(proposal=action.proposal,
                                                                 user=user)
                    if uv.exists():
                        uv = uv[0]
                        uv.boolean_value = value
                        uv.save()
                    else:
                        uv = BooleanVote.objects.create(proposal=action.proposal, user=user, boolean_value=value)
            
            if action == None:
                action_res = CommunityActionBundle.objects.filter(community_post=ts)
                if action_res.exists():
                    action = action_res[0]
                    
                    bundled_actions = list(action.bundled_actions.all())
                    
                    if event['reaction'] in NUMBERS_TEXT.keys():
                        num = NUMBERS_TEXT[event['reaction']]
                        voted_action = bundled_actions[num]
                        
                        
                        user,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                               community_integration=voted_action.community_integration)
                        uv = NumberVote.objects.filter(proposal=voted_action.proposal,
                                                                 user=user)
                        if uv.exists():
                            uv = uv[0]
                            uv.number_value = 1
                            uv.save()
                        else:
                            uv = NumberVote.objects.create(proposal=voted_action.proposal, user=user, number_value=1)
        
    
    return HttpResponse("")
    
