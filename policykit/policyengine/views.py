from django.contrib.auth import get_user
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse, HttpResponseBadRequest
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
    from policyengine.models import CommunityUser, CommunityRole, PlatformPolicy, ConstitutionPolicy

    user = get_user(request)

    users = CommunityUser.objects.filter(community=user.community)
    roles = CommunityRole.objects.filter(community=user.community)
    platform_policies = PlatformPolicy.objects.filter(community=user.community)
    constitution_policies = ConstitutionPolicy.objects.filter(community=user.community)

    # Indexing entries by username/name allows retrieval in O(1) rather than O(n)
    user_data = {}
    for u in users:
        user_data[u.username] = {
            'readable_name': u.readable_name,
            'roles': []
        }

    role_data = {}
    for r in roles:
        role_data[r.role_name] = {
            'permissions': [],
            'users': []
        }
        for p in r.permissions.all():
            role_data[r.role_name]['permissions'].append({ 'name': p.name })
        for u in r.user_set.all():
            cu = u.communityuser
            role_data[r.role_name]['users'].append({ 'username': cu.readable_name })
            user_data[cu.username]['roles'].append({ 'name': r.role_name })

    platform_policy_data = {}
    for pp in platform_policies:
        platform_policy_data[pp.id] = {
            'name': pp.name,
            'description': pp.description,
            'is_bundled': pp.is_bundled,
            'filter': pp.filter,
            'initialize': pp.initialize,
            'check': pp.check,
            'notify': pp.notify,
            'success': pp.success,
            'fail': pp.fail
        }

    constitution_policy_data = {}
    for cp in constitution_policies:
        constitution_policy_data[cp.id] = {
            'name': cp.name,
            'description': cp.description,
            'is_bundled': cp.is_bundled,
            'filter': cp.filter,
            'initialize': cp.initialize,
            'check': cp.check,
            'notify': cp.notify,
            'success': cp.success,
            'fail': cp.fail
        }

    return render(request, 'policyengine/v2/index.html', {
        'server_url': SERVER_URL,
        'user': user,
        'users': user_data,
        'roles': role_data,
        'platform_policies': platform_policy_data,
        'constitution_policies': constitution_policy_data
    })

def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('/login')

def editor(request):
    from policyengine.models import PlatformPolicy, ConstitutionPolicy

    type = request.GET.get('type')
    policy_id = request.GET.get('policy')

    if policy_id:
        policy = None
        if type == 'Platform':
            policy = PlatformPolicy.objects.filter(id=policy_id)[0]
        elif type == 'Constitution':
            policy = ConstitutionPolicy.objects.filter(id=policy_id)[0]
        else:
            return HttpResponseBadRequest()

        return render(request, 'policyengine/v2/editor.html', {
            'server_url': SERVER_URL,
            'user': get_user(request),
            'policy': policy_id,
            'name': policy.name,
            'description': policy.description,
            'filter': policy.filter,
            'initialize': policy.initialize,
            'check': policy.check,
            'notify': policy.notify,
            'success': policy.success,
            'fail': policy.fail
        })

    return render(request, 'policyengine/v2/editor.html', {
        'server_url': SERVER_URL,
        'user': get_user(request)
    })

def selectrole(request):
    from policyengine.models import CommunityRole

    user = get_user(request)
    operation = request.GET.get('operation')

    roles = CommunityRole.objects.filter(community=user.community)

    return render(request, 'policyengine/v2/role_select.html', {
        'server_url': SERVER_URL,
        'user': user,
        'roles': roles,
        'operation': operation
    })

def roleeditor(request):
    from policyengine.models import CommunityRole

    user = get_user(request)
    operation = request.GET.get('operation')

    roles = CommunityRole.objects.filter(community=user.community)
    permissions = []
    for r in roles:
        for p in r.permissions.all():
            permissions.append({ 'name': p.name })

    return render(request, 'policyengine/v2/role_editor.html', {
        'server_url': SERVER_URL,
        'user': user,
        'permissions': permissions,
        'operation': operation
    })

def selectpolicy(request):
    from policyengine.models import PlatformPolicy, ConstitutionPolicy

    user = get_user(request)
    policies = None
    type = request.GET.get('type')
    operation = request.GET.get('operation')

    if type == 'Platform':
        policies = PlatformPolicy.objects.filter(community=user.community)
    elif type == 'Constitution':
        policies = ConstitutionPolicy.objects.filter(community=user.community)
    else:
        return HttpResponseBadRequest()

    return render(request, 'policyengine/v2/policy_select.html', {
        'server_url': SERVER_URL,
        'user': get_user(request),
        'policies': policies,
        'type': type,
        'operation': operation
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
    from policyengine.models import StarterKit, PlatformPolicy, ConstitutionPolicy, CommunityRole, CommunityUser, Proposal, Community
    from django.contrib.auth.models import Permission

    starterkit_name = request.POST['starterkit']
    community_name = request.POST['community_name']
    creator_token = request.POST['creator_token']
    platform = request.POST['platform']

    starter_kit = StarterKit.objects.get(name=starterkit_name, platform=platform)

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

@csrf_exempt
def policy_action_save(request):
    from policyengine.models import PlatformPolicy, ConstitutionPolicy, PolicykitAddConstitutionPolicy, PolicykitAddPlatformPolicy, PolicykitChangeConstitutionPolicy, PolicykitChangePlatformPolicy

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    if data['type'] == 'Constitution' and data['operation'] == 'Add':
        action = PolicykitAddConstitutionPolicy()
        action.is_bundled = data['is_bundled']
    elif data['type'] == 'Platform' and data['operation'] == 'Add':
        action = PolicykitAddPlatformPolicy()
        action.is_bundled = data['is_bundled']
    elif data['type'] == 'Constitution' and data['operation'] == 'Change':
        action = PolicykitChangeConstitutionPolicy()
        action.constitution_policy = ConstitutionPolicy.objects.get(id=data['policy'])
    elif data['type'] == 'Platform' and data['operation'] == 'Change':
        action = PolicykitChangePlatformPolicy()
        action.platform_policy = PlatformPolicy.objects.get(id=data['policy'])
    else:
        return HttpResponseBadRequest()

    action.community = user.community
    action.initiator = user
    action.name = data['name']
    action.description = data['description']
    action.filter = data['filter']
    action.initialize = data['initialize']
    action.check = data['check']
    action.notify = data['notify']
    action.success = data['success']
    action.fail = data['fail']
    action.save()

    return HttpResponse()

@csrf_exempt
def policy_action_remove(request):
    from policyengine.models import PlatformPolicy, ConstitutionPolicy, PolicykitRemoveConstitutionPolicy, PolicykitRemovePlatformPolicy

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    if data['type'] == 'Constitution':
        action = PolicykitRemoveConstitutionPolicy()
        action.constitution_policy = ConstitutionPolicy.objects.get(id=data['policy'])
    elif data['type'] == 'Platform':
        action = PolicykitRemovePlatformPolicy()
        action.platform_policy = PlatformPolicy.objects.get(id=data['policy'])
    else:
        return HttpResponseBadRequest()

    action.community = user.community
    action.initiator = user
    action.save()

    return HttpResponse()

@csrf_exempt
def role_action_save(request):
    from policyengine.models import CommunityRole, PolicykitAddRole

    logger.info('test')

    data = json.loads(request.body)
    user = get_user(request)

    logger.info(data['name'])

    action = PolicykitAddRole()
    action.name = data['name']
    action.permissions = Permission.objects.filter(name__in=data['permissions'])
    action.community = user.community
    action.initiator = user
    action.save()

    logger.info('role saved')

    return HttpResponse()
