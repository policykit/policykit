from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
from policyengine.filter import *
from policyengine.exceptions import NonWhitelistedCodeError
from policyengine.models import *
import urllib.request
import urllib.parse
import logging
import json


logger = logging.getLogger(__name__)

def exec_code(code, wrapperStart, wrapperEnd, globals=None, locals=None):
    """try:
        filter_code(code)
    except NonWhitelistedCodeError as e:
        logger.error(e)
        return"""

    lines = ['  ' + item for item in code.splitlines()]
    code = wrapperStart + '\r\n'.join(lines) + wrapperEnd
    logger.info('built code')
    logger.info(code)

    exec(code, globals, locals)
    logger.info('ran exec')

def filter_policy(policy, action):
    _locals = locals()

    wrapper_start = "def filter(policy, action):\r\n"

    wrapper_end = "\r\nfilter_pass = filter(policy, action)"

    exec_code(policy.filter, wrapper_start, wrapper_end, None, _locals)

    if _locals.get('filter_pass'):
        return _locals['filter_pass']
    else:
        return False

def initialize_policy(policy, action):
    _locals = locals()
    _globals = globals()

    wrapper_start = "def initialize(policy, action):\r\n"

    wrapper_end = "\r\ninitialize(policy, action)"

    exec_code(policy.initialize, wrapper_start, wrapper_end, _globals, _locals)

    policy.has_notified = True
    policy.save()

def check_policy(policy, action):
    from policyengine.models import Proposal, CommunityUser, BooleanVote, NumberVote

    users = CommunityUser.objects.filter(community=policy.community)
    boolean_votes = BooleanVote.objects.filter(proposal=action.proposal)
    number_votes = NumberVote.objects.filter(proposal=action.proposal)

    _locals = locals()

    wrapper_start = "def check(policy, action, users, boolean_votes, number_votes):\r\n"
    wrapper_start += "  PASSED = 'passed'\r\n  FAILED = 'failed'\r\n  PROPOSED = 'proposed'\r\n"

    wrapper_end = "\r\npolicy_pass = check(policy, action, users, boolean_votes, number_votes)"

    exec_code(policy.check, wrapper_start, wrapper_end, None, _locals)

    if _locals.get('policy_pass'):
        return _locals['policy_pass']
    else:
        return Proposal.PROPOSED

def notify_policy(policy, action):
    _locals = locals()

    wrapper_start = "def notify(policy, action):\r\n"

    wrapper_end = "\r\nnotify(policy, action)"

    exec_code(policy.notify, wrapper_start, wrapper_end, None, _locals)

def pass_policy(policy, action):
    _locals = locals()

    wrapper_start = "def success(policy, action):\r\n"

    wrapper_end = "\r\nsuccess(policy, action)"

    logger.info('about to run exec code')
    exec_code(policy.success, wrapper_start, wrapper_end, None, _locals)

def fail_policy(policy, action):
    _locals = locals()
    
    wrapper_start = "def fail(policy, action):\r\n"

    wrapper_end = "\r\nfail(policy, action)"

    exec_code(policy.fail, wrapper_start, wrapper_end, None, _locals)

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

@csrf_exempt
def initialize_starterkit():
    starterkit_name = request.POST['staterkit']
    community_name = request.POST['community_name']
    
    starter_kit = StarterKit.objects.get(name=starterkit_name)
    community = Community.objects.get(community_name=community_name)
    
    for policy in starter_kit.genericpolicy_set.all():
        if policy.is_constitution:
            policy.make_constitution_policy(community)
        else:
            policy.make_community_policy(community)
    
    for role in starterkit.genericrole_set.all():
        role.make_community_role(community)

    response = redirect('/login?success=true')
    return response

#pass in the community
