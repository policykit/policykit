from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
import urllib.request
import urllib.parse
import logging
import json

PROPOSED = 'proposed'
FAILED = 'failed'
PASSED = 'passed'

logger = logging.getLogger(__name__)


def check_filter_code(policy, action):
    _locals = locals()
     
    wrapper_start = "def filter():\r\n"
    wrapper_end = "\r\nfilter_pass = filter()"
     
    lines = ['  ' + item for item in policy.policy_filter_code.splitlines()]
    filter_str = '\r\n'.join(lines)
    filter_code = wrapper_start + filter_str + wrapper_end
     
     
    exec(filter_code, globals(), _locals)
    
    if _locals.get('filter_pass'):
        return _locals['filter_pass']
    else:
        return False



def initialize_code(policy, action):
    exec(policy.policy_init_code, globals(), locals())
    
    policy.has_notified = True
    policy.save()
    


def check_policy_code(policy, action):
    _locals = locals()
    exec(policy.policy_conditional_code, globals(), _locals)
    
    if _locals.get('action_pass'):
        return _locals['action_pass']
    else:
        return PROPOSED


def execute_community_action(action, delete_policykit_post=True):
    from policyengine.models import LogAPICall, CommunityUser
    
    logger.info('here')

    community = action.community
    obj = action
    
    if not obj.community_origin or (obj.community_origin and obj.community_revert):
        logger.info('EXECUTING ACTION BELOW:')
        call = community.API + obj.ACTION
        logger.info(call)
    
        
        obj_fields = []
        for f in obj._meta.get_fields():
            if f.name not in ['polymorphic_ctype',
                              'community',
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
                data['token'] = community.access_token
        elif obj.AUTH == "admin_user":
            admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
            data['token'] = admin_user.access_token
        else:
            data['token'] = community.access_token
            
        
        for item in obj_fields:
            try :
                if item != 'id':
                    value = getattr(obj, item)
                    data[item] = value
            except obj.DoesNotExist:
                continue

        res = LogAPICall.make_api_call(community, data, call)
        
        
        # delete PolicyKit Post
        if delete_policykit_post:
            posted_action = None
            if action.is_bundled:
                bundle = action.communityactionbundle_set.all()
                if bundle.exists():
                    posted_action = bundle[0]
            else:
                posted_action = action
                
            if posted_action.community_post:
                admin_user = CommunityUser.objects.filter(is_community_admin=True)[0]
                values = {'token': admin_user.access_token,
                          'ts': posted_action.community_post,
                          'channel': obj.channel
                        }
                call = community.API + 'chat.delete'
                _ = LogAPICall.make_api_call(community, values, call)

        
        
        if res['ok']:
            clean_up_proposals(action, True)
        else:
            error_message = res['error']
            logger.info(error_message)
            clean_up_proposals(action, False)

    else:
        clean_up_proposals(action, True)


def clean_up_proposals(action, executed):
    from policyengine.models import Proposal, CommunityActionBundle
    
    if action.is_bundled:
        bundle = action.communityactionbundle_set.all()
        if bundle.exists():
            bundle = bundle[0]
            # TO DO - remove all of this
            if bundle.bundle_type == CommunityActionBundle.ELECTION:
                for a in bundle.bundled_actions.all():
                    if a != action:
                        p = a.proposal
                        p.status = Proposal.FAILED
                        p.save()
            p = bundle.proposal
            if executed:
                p.status = Proposal.PASSED
            else:
                p.status = Proposal.FAILED
            p.save()
            
        
    p = action.proposal
    if executed:
        p.status = Proposal.PASSED
    else:
        p.status = Proposal.FAILED
    p.save()
            
            
            
    