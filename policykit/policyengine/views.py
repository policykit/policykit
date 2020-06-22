from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
import urllib.request
import urllib.parse
import logging
import json



logger = logging.getLogger(__name__)


def check_filter_code(policy, action):
    _locals = locals()
     
    wrapper_start = "def filter():\r\n"
    wrapper_end = "\r\nfilter_pass = filter()"
     
    lines = ['  ' + item for item in policy.policy_filter_code.splitlines()]
    filter_str = '\r\n'.join(lines)
    filter_code = wrapper_start + filter_str + wrapper_end
     
     
    exec(filter_code, None, _locals)
    
    if _locals.get('filter_pass'):
        return _locals['filter_pass']
    else:
        return False



def initialize_code(policy, action):
    exec(policy.policy_init_code, globals(), locals())
    
    policy.has_notified = True
    policy.save()
    


def check_policy_code(policy, action):
    from policyengine.models import Proposal, CommunityUser, BooleanVote, NumberVote

    users = CommunityUser.objects.filter(community=policy.community)
    boolean_votes = BooleanVote.objects.filter(proposal=action.proposal)
    number_votes = NumberVote.objects.filter(proposal=action.proposal)
    
    _locals = locals()
    
    wrapper_start = "def check(policy, action, users, boolean_votes, number_votes):\r\n"
    wrapper_start += "  PASSED = 'passed'\r\n  FAILED = 'failed'\r\n  PROPOSED = 'proposed'\r\n"
    
    wrapper_end = "\r\npolicy_pass = check(policy, action, users, boolean_votes, number_votes)"
     
    lines = ['  ' + item for item in policy.policy_conditional_code.splitlines()]
    check_str = '\r\n'.join(lines)
    check_code = wrapper_start + check_str + wrapper_end

    exec(check_code, None, _locals)
    
    if _locals.get('policy_pass'):
        return _locals['policy_pass']
    else:
        return Proposal.PROPOSED




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
            
            
            
    