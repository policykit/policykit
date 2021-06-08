from django.shortcuts import render
from django.http import HttpResponse, HttpResponseRedirect
from urllib import parse
import urllib.request
# from policykit.settings import SLACK_CLIENT_SECRET, SLACK_CLIENT_ID
from django.contrib.auth import login, authenticate
import logging
from django.shortcuts import redirect
import json
from integrations.slack.models import SlackStarterKit, SlackCommunity, SlackUser, SlackRenameConversation, SlackJoinConversation, SlackPostMessage, SlackPinMessage
from policyengine.models import *
from django.contrib.auth.models import User, Group
from django.views.decorators.csrf import csrf_exempt
import datetime
from django.conf import settings
import requests

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


NUMBERS = {0: 'zero',
           1: 'one',
           2: 'two',
           3: 'three',
           4: 'four',
           5: 'five',
           6: 'six',
           7: 'seven',
           8: 'eight',
           9: 'nine'}


def slack_login(request):
    """redirect after metagov has gotten the slack user token"""
    logger.info(f"slack_login")
    logger.info(request.GET)
    user_token = request.GET.get('user_token')
    team_id = request.GET.get('team_id')
    user = authenticate(request, user_token=user_token, team_id=team_id, platform="slack")
    if user:
        login(request, user)
        response = redirect('/main')
    else:
        response = redirect('/login?error=policykit_not_yet_installed_to_that_community')
    return response

def slack_install(request):
    #TODO if error
    # response = redirect('/login?error=cancel')
    # return response
    
    state = request.GET.get('state') #TODO need to validate the request!!!!
    team_id = request.GET.get('team_id')
    metagov_community_slug = request.GET.get('community')

    

    logger.info(f">>>> Creating SlackCommunity {team_id}, {metagov_community_slug}")
    from policyengine.models import MetaCommunity
    pk = int(metagov_community_slug.split("-")[1]) # FIXME use a manager
    meta_community = MetaCommunity.objects.get(pk=pk)
    # the SlackCommunity will be linked to this MetaCommunity

    # redirect here from metagov authorization, and check the `community` param
    # fetch user list from metagov


    # Checks that user is admin
    # dataAdmin = parse.urlencode({
    #     'token': res['access_token'],
    #     'user': res['authed_user']['id']
    # }).encode()
    # reqInfo = urllib.request.Request('https://slack.com/api/users.info', data=dataAdmin)
    # respInfo = urllib.request.urlopen(reqInfo)
    # resInfo = json.loads(respInfo.read())

    # if resInfo['user']['is_admin'] == False:
    #     response = redirect('/login?error=user_is_not_an_admin')
    #     return response

    
    # curl -iX POST "https://prototype.metagov.org/api/internal/action/slack.method" -H  "accept: application/json" -H  "X-Metagov-Community: slack-tmq3pkxt9" -d '{"parameters":{"method_name":"team.info"}}'

    # Getting team info from Slack
    response = requests.post(f"{settings.METAGOV_URL}/api/internal/action/slack.method", json={"parameters": {"method_name":"team.info"}}, headers={"X-Metagov-Community": metagov_community_slug})
    if not response.ok:
        raise Exception(f"Error performing action {action_type}: {response.status_code} {response.reason} {response.text}")
    data = response.json()
    
    team = data["team"]
    logger.info(f"TEAM: {team}")
    team_id = team["id"]
    readable_name = team["name"] #update MetaCommunity

    s = SlackCommunity.objects.filter(team_id=team_id)
    community = None
    #TODO: metagov get team info
    user_group,_ = CommunityRole.objects.get_or_create(role_name = "Base User", name="Slack: " + team_id + ": Base User")

    # user = SlackUser.objects.filter(username=res['authed_user']['id'])

    if not s.exists():
        logger.info("Creating new SlackCommunity")
        community = SlackCommunity.objects.create(
            meta_community=meta_community,
            community_name=readable_name, #res['team']['name']
            team_id=team_id,
            
            # bot_id = res['bot_user_id'],
            # access_token=res['access_token'],
            base_role=user_group
        )
        user_group.community = community
        user_group.save()

        #get the list of users, create SlackUser object for each user
        # TODO GET metagov action/slack.method
        # X-Metagov-Community: community.meta_community.metagov_name
        data2 = parse.urlencode({
            'token':community.access_token
        }).encode()

        req2 = urllib.request.Request('https://slack.com/api/users.list', data=data2)
        resp2 = urllib.request.urlopen(req2)
        res2 = json.loads(resp2.read().decode('utf-8'))

        #https://api.slack.com/methods/users.list
        if res2['ok']:
            for new_user in res2['members']:
                if (not new_user['deleted']) and (not new_user['is_bot']) and (new_user['id'] != 'USLACKBOT'):
                    # if new_user['id'] == res['authed_user']['id']:
                    #     u,_ = SlackUser.objects.get_or_create(
                    #         username=res['authed_user']['id'],
                    #         readable_name=new_user['real_name'],
                    #         access_token=res['authed_user']['access_token'],
                    #         is_community_admin=True, #XXX need this
                    #         community=community
                    #     )
                    # else:
                    u,_ = SlackUser.objects.get_or_create(
                        username=new_user['id'],
                        readable_name=new_user['real_name'],
                        avatar=new_user['profile']['image_24'],
                        community=community
                    )
                    # u.save()
        
        context = {
            "starterkits": [kit.name for kit in SlackStarterKit.objects.all()],
            "community_name": community.community_name,
            "creator_token": None,
            # "creator_token": res['authed_user']['access_token'], #what is this for
            "platform": "slack"
        }
        return render(request, "policyadmin/init_starterkit.html", context)
        
    else:
        logger.info("community already exists..leaving it as is")
        # community = s[0]
        # community.community_name = res['team']['name']
        # community.team_id = res['team']['id']
        # community.bot_id = res['bot_user_id']
        # community.access_token = res['access_token']
        # community.save()

        response = redirect('/login?success=true')
        return response


def is_policykit_bot_action(community, event):
    return event.get('user') == community.bot_id

def is_policykit_action(integration, test_a, test_b, api_name):
    current_time_minus = datetime.datetime.now() - datetime.timedelta(seconds=2)
    logs = LogAPICall.objects.filter(proposal_time__gte=current_time_minus, call_type=api_name)

    if logs.exists():
        for log in logs:
            j_info = json.loads(log.extra_info)
            if test_a == j_info[test_b]:
                return True

    return False

def maybe_create_new_api_action(community, event):
    new_api_action = None
    if event.get('type') == "channel_rename":
        if not is_policykit_action(community, event['channel']['name'], 'name', SlackRenameConversation.ACTION):
            new_api_action = SlackRenameConversation()
            new_api_action.community = community
            new_api_action.name = event['channel']['name']
            new_api_action.channel = event['channel']['id']

            u,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                  community=community)
            new_api_action.initiator = u
            prev_names = new_api_action.get_channel_info()
            new_api_action.prev_name = prev_names[0]

    elif event.get('type') == 'message' and event.get('subtype') == None:
        if not is_policykit_action(community, event['text'], 'text', SlackPostMessage.ACTION):
            new_api_action = SlackPostMessage()
            new_api_action.community = community
            new_api_action.text = event['text']
            new_api_action.channel = event['channel']
            new_api_action.time_stamp = event['ts']

            u,_ = SlackUser.objects.get_or_create(username=event['user'], community=community)

            new_api_action.initiator = u

    elif event.get('type') == "member_joined_channel":
        if not is_policykit_action(community, event['channel'], 'channel', SlackJoinConversation.ACTION):
            new_api_action = SlackJoinConversation()
            new_api_action.community = community
            if event.get('inviter'):
                u,_ = SlackUser.objects.get_or_create(username=event['inviter'],
                                                        community=community)
                new_api_action.initiator = u
            else:
                u,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                        community=community)
                new_api_action.initiator = u
            new_api_action.users = event.get('user')
            new_api_action.channel = event['channel']

    elif event.get('type') == 'pin_added':
        if not is_policykit_action(community, event['channel_id'], 'channel', SlackPinMessage.ACTION):
            new_api_action = SlackPinMessage()
            new_api_action.community = community

            u,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                    community=community)
            new_api_action.initiator = u
            new_api_action.channel = event['channel_id']
            new_api_action.timestamp = event['item']['message']['ts']

    return new_api_action

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
        community = SlackCommunity.objects.get(team_id=team_id)
        admin_user = SlackUser.objects.filter(is_community_admin=True)[0]

        new_api_action = None
        if not is_policykit_bot_action(community, event):
            new_api_action = maybe_create_new_api_action(community, event)

        if new_api_action is not None:
            new_api_action.community_origin = True
            new_api_action.is_bundled = False
            new_api_action.save() # save triggers policy evaluation
        else:
            logger.info(f"No PlatformAction created for event '{event.get('type')}'")

        if event.get('type') == 'reaction_added':
            ts = event['item']['ts']
            action = None
            action_res = PlatformAction.objects.filter(community_post=ts)
            if action_res.exists():
                action = action_res[0]

                if event['reaction'] == '+1' or event['reaction'] == '-1':
                    if event['reaction'] == '+1':
                        value = True
                    elif event['reaction'] == '-1':
                        value = False

                    user,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                            community=action.community)
                    uv = BooleanVote.objects.filter(proposal=action.proposal,
                                                                 user=user)
                    if uv.exists():
                        uv = uv[0]
                        uv.boolean_value = value
                        uv.save()
                    else:
                        uv = BooleanVote.objects.create(proposal=action.proposal, user=user, boolean_value=value)

            if action == None:
                action_res = PlatformActionBundle.objects.filter(community_post=ts)
                if action_res.exists():
                    action = action_res[0]

                    bundled_actions = list(action.bundled_actions.all())

                    if event['reaction'] in NUMBERS_TEXT.keys():
                        num = NUMBERS_TEXT[event['reaction']]
                        voted_action = bundled_actions[num]

                        user,_ = SlackUser.objects.get_or_create(username=event['user'],
                                                               community=voted_action.community)
                        uv = NumberVote.objects.filter(proposal=voted_action.proposal,
                                                                 user=user)
                        if uv.exists():
                            uv = uv[0]
                            uv.number_value = 1
                            uv.save()
                        else:
                            uv = NumberVote.objects.create(proposal=voted_action.proposal, user=user, number_value=1)

    return HttpResponse("")

def post_policy(policy, action, users=None, post_type='channel', template=None, channel=None):
    from policyengine.models import LogAPICall, PlatformActionBundle

    if action.action_type == "PlatformActionBundle" and action.bundle_type == PlatformActionBundle.ELECTION:
        policy_message_default = "This action is governed by the following policy: " + policy.explanation + '. Decide between options below:\n'

        bundled_actions = action.bundled_actions.all()
        for num, a in enumerate(bundled_actions):
            policy_message_default += ':' + NUMBERS[num] + ': ' + str(a) + '\n'
    else:
        policy_message_default = "This action is governed by the following policy: " + policy.description + '. Vote with :thumbsup: or :thumbsdown: on this post.'

    values = {'token': policy.community.access_token}

    if not template:
        policy_message = policy_message_default
    else:
        policy_message = template

    values['text'] = policy_message

    # mpim - all users
    # im each user
    # channel all users
    # channel ephemeral users

    if post_type == "mpim":
        api_call = 'chat.postMessage'
        usernames = [user.username for user in users]
        info = {'token': policy.community.access_token}
        info['users'] = ','.join(usernames)
        call = policy.community.API + 'conversations.open'
        res = LogAPICall.make_api_call(policy.community, info, call)
        channel = res['channel']['id']
        values['channel'] = channel

        call = policy.community_integration.API + api_call
        res = LogAPICall.make_api_call(policy.community, values, call)

        action.community_post = res['ts']
        action.save()

    elif post_type == 'im':
        api_call = 'chat.postMessage'
        usernames = [user.username for user in users]

        for username in usernames:
            info = {'token': policy.community.access_token}
            info['users'] = username
            call = policy.community.API + 'conversations.open'
            res = LogAPICall.make_api_call(policy.community, info, call)
            channel = res['channel']['id']
            values['channel'] = channel

            call = policy.community.API + api_call
            res = LogAPICall.make_api_call(policy.community, values, call)

            action.community_post = res['ts']
            action.save()

    elif post_type == 'ephemeral':
        api_call = 'chat.postEphemeral'
        usernames = [user.username for user in users]

        for username in usernames:
            values['user'] = username

            if channel:
                values['channel'] = channel
            else:
                if action.action_type == "PlatformAction":
                    values['channel'] = action.channel
                else:
                    a = action.bundled_actions.all()[0]
                    values['channel'] = a.channel
            call = policy.community.API + api_call

            res = LogAPICall.make_api_call(policy.community, values, call)

            action.community_post = res['ts']
            action.save()
    elif post_type == 'channel':
        api_call = 'chat.postMessage'
        if channel:
            values['channel'] = channel
        else:
            if action.action_type == "PlatformAction":
                values['channel'] = action.channel
            else:
                a = action.bundled_actions.all()[0]
                values['channel'] = a.channel

        call = policy.community.API + api_call
        res = LogAPICall.make_api_call(policy.community, values, call)

        action.community_post = res['ts']
        action.save()
