from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
import urllib.request
import urllib.parse
import logging
import json

logger = logging.getLogger(__name__)

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


def check_filter_code(policy, action):
    from policyengine.models import Proposal, BooleanVote, NumberVote, CommunityUser, CommunityActionBundle
    _locals = locals()
    exec(policy.policy_filter_code, globals(), _locals)
    
    if _locals.get('action_pass'):
        return _locals['action_pass']
    else:
        return False



def initialize_code(policy, action):
    from policyengine.models import Proposal, BooleanVote, NumberVote, CommunityUser, CommunityActionBundle
    exec(policy.policy_init_code, globals(), locals())
    


def check_policy_code(policy, action):
    from policyengine.models import Proposal, BooleanVote, NumberVote, CommunityUser, CommunityActionBundle
    _locals = locals()
    exec(policy.policy_conditional_code, globals(), _locals)
    
    if _locals.get('policy_pass'):
        return _locals['policy_pass']
    else:
        return Proposal.PROPOSED


def post_policy(policy, action, post_type='channel', users=None, template=None, channel=None):
    from policyengine.models import LogAPICall
    
    if action.action_type == "CommunityActionBundle":
        policy_message_default = "This action is governed by the following policy: " + policy.explanation + '. Vote below:\n'
        bundled_actions = action.bundled_actions.all()
        for num, a in enumerate(bundled_actions):
            policy_message_default += ':' + NUMBERS[num] + ': ' + str(a.api_action) + '\n'
    else:
        policy_message_default = "This action is governed by the following policy: " + policy.explanation + '. Vote with :thumbsup: or :thumbsdown: on this post.'
    
    values = {'token': policy.community_integration.access_token}
    
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
        info = {'token': policy.community_integration.access_token}
        info['users'] = ','.join(usernames)
        call = policy.community_integration.API + 'conversations.open'
        res = LogAPICall.make_api_call(policy.community_integration, info, call)
        channel = res['channel']['id']
        values['channel'] = channel
        
        call = policy.community_integration.API + api_call
        res = LogAPICall.make_api_call(policy.community_integration, values, call)
        
        action.community_post = res['ts']
        action.save()
        
    elif post_type == 'im':
        api_call = 'chat.postMessage'
        usernames = [user.username for user in users]
        
        for username in usernames:
            info = {'token': policy.community_integration.access_token}
            info['users'] = username
            call = policy.community_integration.API + 'conversations.open'
            res = LogAPICall.make_api_call(policy.community_integration, info, call)
            channel = res['channel']['id']
            values['channel'] = channel
            
            call = policy.community_integration.API + api_call
            res = LogAPICall.make_api_call(policy.community_integration, values, call)
            
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
                if action.action_type == "CommunityAction":
                    values['channel'] = action.api_action.channel
                else:
                    a = action.bundled_actions.all()[0]
                    values['channel'] = a.api_action.channel
            call = policy.community_integration.API + api_call
            
            res = LogAPICall.make_api_call(policy.community_integration, values, call)
            
            action.community_post = res['ts']
            action.save()
    elif post_type == 'channel':
        api_call = 'chat.postMessage'
        if channel:
            values['channel'] = channel
        else:
            if action.action_type == "CommunityAction":
                values['channel'] = action.api_action.channel
            else:
                a = action.bundled_actions.all()[0]
                values['channel'] = a.api_action.channel
                    
        call = policy.community_integration.API + api_call
        res = LogAPICall.make_api_call(policy.community_integration, values, call)
        
        action.community_post = res['ts']
        action.save()


def execute_action(action):
    from policyengine.models import LogAPICall, CommunityUser
    
    logger.info('here')

    community_integration = action.community_integration
    obj = action.api_action
    
    if not obj.community_origin or (obj.community_origin and obj.community_revert):
        logger.info('EXECUTING ACTION BELOW:')
        call = community_integration.API + obj.ACTION
        logger.info(call)
    
        
        obj_fields = []
        for f in obj._meta.get_fields():
            if f.name not in ['polymorphic_ctype',
                              'community_integration',
                              'initiator',
                              'communityapi_ptr',
                              'communityaction',
                              'communityactionbundle',
                              'community_revert',
                              'community_origin',
                              'is_bundled'
                              ]:
                obj_fields.append(f.name) 
        
        data = {}
        
        if obj.AUTH == "user":
            data['token'] = action.proposal.author.access_token
            if not data['token']:
                admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
                data['token'] = admin_user.access_token
        elif obj.AUTH == "admin_bot":
            if action.proposal.author.is_community_admin:
                data['token'] = action.proposal.author.access_token
            else:
                data['token'] = community_integration.access_token
        elif obj.AUTH == "admin_user":
            admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
            data['token'] = admin_user.access_token
        else:
            data['token'] = community_integration.access_token
            
        
        for item in obj_fields:
            try :
                if item != 'id':
                    value = getattr(obj, item)
                    data[item] = value
            except obj.DoesNotExist:
                continue

        res = LogAPICall.make_api_call(community_integration, data, call)
        
        if action.community_post:
            admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
            values = {'token': admin_user.access_token,
                      'ts': action.community_post,
                      'channel': obj.channel
                    }
            call = community_integration.API + 'chat.delete'
            _ = LogAPICall.make_api_call(community_integration, values, call)
        
        if res['ok']:
            from policyengine.models import Proposal
            p = action.proposal
            p.status = Proposal.PASSED
            p.save()
        else:
            error_message = res['error']
            logger.info(error_message)

    else:
        from policyengine.models import Proposal
        p = action.proposal
        p.status = Proposal.PASSED
        p.save()

