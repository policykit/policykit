from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
from policyengine.filter import *
from policyengine.exceptions import NonWhitelistedCodeError
import urllib.request
import urllib.parse
import logging
import json


logger = logging.getLogger(__name__)

def homepage(request):
    return render(request, 'policyengine/home.html', {})
    

def exec_code(code, wrapperStart, wrapperEnd, globals=None, locals=None):
    try:
        filter_code(code)
    except NonWhitelistedCodeError as e:
        logger.error(e)
        return

    lines = ['  ' + item for item in code.splitlines()]
    code = wrapperStart + '\r\n'.join(lines) + wrapperEnd

    exec(code, globals, locals)

def filter_policy(policy, action):
    _locals = locals()

    wrapper_start = "def filter():\r\n"

    wrapper_end = "\r\nfilter_pass = filter()"

    exec_code(policy.filter, wrapper_start, wrapper_end, None, _locals)

    if _locals.get('filter_pass'):
        return _locals['filter_pass']
    else:
        return False

def initialize_policy(policy, action):
    wrapper_start = "def initialize():\r\n"

    wrapper_end = "\r\ninitialize()"

    exec_code(policy.initialize, wrapper_start, wrapper_end, globals(), locals())

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
    wrapper_start = "def notify():\r\n"

    wrapper_end = "\r\nnotify()"

    exec_code(policy.notify, wrapper_start, wrapper_end, None, locals())

def pass_policy(policy, action):
    wrapper_start = "def success(action):\r\n"

    wrapper_end = "\r\nsuccess(action)"

    exec_code(policy.success, wrapper_start, wrapper_end, None, locals())

def fail_policy(policy, action):
    wrapper_start = "def fail():\r\n"

    wrapper_end = "\r\nfail()"

    exec_code(policy.fail, wrapper_start, wrapper_end, None, locals())

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
