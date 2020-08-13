from django.contrib.auth import get_user
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from policyengine.filter import *
from policykit.settings import SERVER_URL
import urllib.request
import urllib.parse
import logging
import json
import parser


logger = logging.getLogger(__name__)

def homepage(request):
    return render(request, 'policyengine/home.html', {})

def v2(request):
    return render(request, 'policyengine/v2/index.html', {
        'server_url': SERVER_URL,
        'user': get_user(request)
    })

def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('/login')

def editor(request):
    return render(request, 'policyengine/v2/editor.html', {
        'server_url': SERVER_URL,
        'user': get_user(request)
    })

def actions(request):
    user = get_user(request)

    return render(request, 'policyengine/v2/actions.html', {
        'server_url': SERVER_URL,
        'user': get_user(request),
    })

def exec_code(code, wrapperStart, wrapperEnd, globals=None, locals=None):
    errors = filter_code(code)
    if len(errors) > 0:
        logger.error('Filter errors:')
        for error in errors:
            logger.error(error.message)
        return

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
    from policyengine.models import Proposal, CommunityUser, BooleanVote, NumberVote

    users = CommunityUser.objects.filter(community=policy.community)

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
    from policyengine.models import Proposal, PlatformActionBundle

    if action.is_bundled:
        bundle = action.platformactionbundle_set.all()
        if bundle.exists():
            bundle = bundle[0]
            # TO DO - remove all of this
            if bundle.bundle_type == PlatformActionBundle.ELECTION:
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
def initialize_starterkit(request):
    from policyengine.models import PlatformPolicy, ConstitutionPolicy, CommunityRole, CommunityUser, Proposal, Community
    from django.contrib.auth.models import Permission
    from redditintegration.models import RedditStarterKit
    from slackintegration.models import SlackStarterKit
    
    starterkit_name = request.POST['starterkit']
    community_name = request.POST['community_name']
    creator_token = request.POST['creator_token']
    platform = request.POST['platform']

    starter_kit = None
    if platform == "slack":
        starter_kit = SlackStarterKit.objects.get(name=starterkit_name)
    elif platform == "reddit":
        starter_kit = RedditStarterKit.objects.get(name=starterkit_name)

    community = Community.objects.get(community_name=community_name)
    starter_kit.init_kit(community, creator_token)

    logger.info('starterkit initialized')
    logger.info('creator_token' + creator_token)

    response = redirect('/login?success=true')
    return response

@csrf_exempt
def error_check(request):
    data = json.loads(request.body)
    code = data['code']

    errors = []

    # Note: only catches first SyntaxError in code
    #   when user fixes this error, then it will catch the next one, and so on
    #   could use linter, but that has false positives sometimes
    #   since syntax errors often affect future code
    try:
        parser.suite(code)
    except SyntaxError as e:
        errors.append({ 'type': 'syntax', 'lineno': e.lineno, 'code': e.text, 'message': str(e) })

    try:
        filter_errors = filter_code(code)
        errors.extend(filter_errors)
    except SyntaxError as e:
        pass

    if len(errors) > 0:
        return JsonResponse({ 'is_error': True, 'errors': errors })
    return JsonResponse({ 'is_error': False })

#pass in the community
