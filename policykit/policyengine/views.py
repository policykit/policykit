from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
import urllib.request
import urllib.parse
import logging
import json

logger = logging.getLogger(__name__)

def check_policy_code(policy, action):
    from policyengine.models import Proposal, UserVote, CommunityUser
    _locals = locals()
    exec(policy.policy_conditional_code, globals(), _locals)
    
    if _locals.get('policy_pass'):
        return _locals['policy_pass']
    else:
        return Proposal.PROPOSED


def check_filter_code(policy, action):
    _locals = locals()
    exec(policy.policy_filter_code, globals(), _locals)
    
    if _locals.get('action_pass'):
        return _locals['action_pass']
    else:
        return False


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
                              'community_post',
                              'communityapi_ptr',
                              'communityaction',
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
        
        if obj.community_post:
            values = {'token': action.proposal.author.access_token,
                      'ts': obj.community_post,
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

