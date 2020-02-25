from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
import urllib.request
import urllib.parse
import logging
import json

logger = logging.getLogger(__name__)

def check_policy_code(policy):
    from policyengine.models import Proposal
    _locals = locals()
    policy_pass = Proposal.PROPOSED
    exec(policy.policy_conditional_code, globals(), _locals)
    return _locals['policy_pass']


def check_filter_code(policy, action):
    _locals = locals()
    action_pass = False
    exec(policy.policy_filter_code, globals(), _locals)
    return _locals['action_pass']


def execute_action(action):
    logger.info('here')
    logger.info('EXECUTING ACTION BELOW:')
    logger.info(action)
    
    community_integration = action.community_integration
    
    obj = action.api_action
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
    else:
        data['token'] = community_integration.access_token
    
    logger.info('here2')
    
    for item in obj_fields:
        try :
            if item != 'id':
                value = getattr(obj, item)
                data[item] = value
        except obj.DoesNotExist:
            continue
    
    data = urllib.parse.urlencode(data).encode('ascii')
    
    logger.info(data)

    response = urllib.request.urlopen(url=call, data=data)
    
    html = response.read()
    
    logger.info(html)
    
    res = json.loads(html)
    
    
    if obj.community_post:
        values = {'token': action.proposal.author.access_token,
                  'ts': obj.community_post,
                  'channel': obj.channel
                }
        data = urllib.parse.urlencode(values)
        data = data.encode('utf-8')
        call_info = community_integration.API + 'chat.delete?'
        req = urllib.request.Request(call_info, data)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        logger.info(res)
    
    
    if res['ok']:
        from policyengine.models import Proposal
        p = action.proposal
        p.status = Proposal.PASSED
        p.save()
    else:
        error_message = res['error']
        logger.info(error_message)
    
