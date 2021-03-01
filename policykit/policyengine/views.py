from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from actstream import action
from actstream.models import model_stream, target_stream, Action
from policyengine.filter import *
from policykit.settings import SERVER_URL
import urllib.request
import urllib.parse
import logging
import json
import parser
import html


logger = logging.getLogger(__name__)

def homepage(request):
    return render(request, 'home.html', {})

@login_required(login_url='/login')
def v2(request):
    from policyengine.models import Community, CommunityUser, CommunityRole, CommunityDoc, PlatformPolicy, ConstitutionPolicy

    user = get_user(request)

    users = CommunityUser.objects.filter(community=user.community)
    roles = CommunityRole.objects.filter(community=user.community)
    docs = CommunityDoc.objects.filter(community=user.community)
    platform_policies = PlatformPolicy.objects.filter(community=user.community)
    constitution_policies = ConstitutionPolicy.objects.filter(community=user.community)

    # Indexing entries by username/name allows retrieval in O(1) rather than O(n)
    user_data = {}
    for u in users:
        user_data[u.username] = {
            'readable_name': u.readable_name,
            'roles': [],
            'avatar': u.avatar
        }

    role_data = {}
    for r in roles:
        role_data[r.role_name] = {
            'description': r.description,
            'permissions': [],
            'users': []
        }
        for p in r.permissions.all():
            role_data[r.role_name]['permissions'].append({ 'name': p.name })
        for u in r.user_set.all():
            cu = u.communityuser
            role_data[r.role_name]['users'].append({ 'username': cu.readable_name })
            user_data[cu.username]['roles'].append({ 'name': r.role_name })

    doc_data = {}
    for d in docs:
        doc_data[d.id] = {
            'name': d.name,
            'text': d.text
        }

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

    action_log_data = []
    for action in Action.objects.all():
        action_data = {
            'actor': action.actor,
            'verb': action.verb,
            'time_elapsed': action.timesince
        }
        action_log_data.append(action_data)

    return render(request, 'policyadmin/dashboard/index.html', {
        'server_url': SERVER_URL,
        'user': user,
        'users': user_data,
        'roles': role_data,
        'docs': doc_data,
        'platform_policies': platform_policy_data,
        'constitution_policies': constitution_policy_data,
        'action_log': action_log_data
    })

def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('/login')

@login_required(login_url='/login')
def documentation(request):
    return render(request, 'policyadmin/dashboard/documentation.html', {})

@login_required(login_url='/login')
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

        return render(request, 'policyadmin/dashboard/editor.html', {
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

    return render(request, 'policyadmin/dashboard/editor.html', {
        'server_url': SERVER_URL,
        'user': get_user(request)
    })

@login_required(login_url='/login')
def selectrole(request):
    from policyengine.models import CommunityRole

    user = get_user(request)
    operation = request.GET.get('operation')

    roles = CommunityRole.objects.filter(community=user.community)

    return render(request, 'policyadmin/dashboard/role_select.html', {
        'server_url': SERVER_URL,
        'user': user,
        'roles': roles,
        'operation': operation
    })

@login_required(login_url='/login')
def roleusers(request):
    from policyengine.models import CommunityRole, CommunityUser

    user = get_user(request)
    operation = request.GET.get('operation')

    roles = CommunityRole.objects.filter(community=user.community)
    users = CommunityUser.objects.filter(community=user.community)

    return render(request, 'policyadmin/dashboard/role_users.html', {
        'server_url': SERVER_URL,
        'roles': roles,
        'users': users,
        'operation': operation
    })

@login_required(login_url='/login')
def roleeditor(request):
    from policyengine.models import CommunityRole

    user = get_user(request)
    operation = request.GET.get('operation')
    role_name = request.GET.get('role')

    roles = CommunityRole.objects.filter(community=user.community)
    permissions = set()
    for r in roles:
        for p in r.permissions.all():
            permissions.add(p.name)

    data = {
        'server_url': SERVER_URL,
        'user': user,
        'permissions': list(sorted(permissions)),
        'operation': operation
    }

    if role_name:
        role = CommunityRole.objects.filter(name=role_name)[0]
        data['role_name'] = role.role_name
        data['name'] = role_name
        data['description'] = role.description
        currentPermissions = []
        for p in role.permissions.all():
            currentPermissions.append(p.name)
        data['currentPermissions'] = currentPermissions

    return render(request, 'policyadmin/dashboard/role_editor.html', data)

@login_required(login_url='/login')
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

    return render(request, 'policyadmin/dashboard/policy_select.html', {
        'server_url': SERVER_URL,
        'user': get_user(request),
        'policies': policies,
        'type': type,
        'operation': operation
    })

@login_required(login_url='/login')
def selectdocument(request):
    from policyengine.models import CommunityDoc

    user = get_user(request)
    documents = None
    operation = request.GET.get('operation')

    documents = CommunityDoc.objects.filter(community=user.community)

    return render(request, 'policyadmin/dashboard/document_select.html', {
        'server_url': SERVER_URL,
        'user': get_user(request),
        'documents': documents,
        'operation': operation
    })

@login_required(login_url='/login')
def documenteditor(request):
    from policyengine.models import CommunityDoc

    user = get_user(request)
    operation = request.GET.get('operation')
    doc_id = request.GET.get('doc')

    data = {
        'server_url': SERVER_URL,
        'user': user,
        'operation': operation
    }

    if doc_id:
        doc = CommunityDoc.objects.filter(id=doc_id)[0]
        data['name'] = doc.name
        data['text'] = doc.text

    return render(request, 'policyadmin/dashboard/document_editor.html', data)

@login_required(login_url='/login')
def actions(request):
    user = get_user(request)

    return render(request, 'policyadmin/dashboard/actions.html', {
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

    try:
        exec(code, globals, locals)
    except Exception as e:
        logger.exception('Got exception in exec_code:')
        raise

def filter_policy(policy, action):
    from policyengine.models import CommunityUser

    users = CommunityUser.objects.filter(community=policy.community)
    _locals = locals()

    wrapper_start = "def filter(policy, action, users):\r\n"

    wrapper_end = "\r\nfilter_pass = filter(policy, action, users)"

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

    wrapper_start = "def initialize(policy, action, users):\r\n"

    wrapper_end = "\r\ninitialize(policy, action, users)"

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
    from policyengine.models import CommunityUser

    users = CommunityUser.objects.filter(community=policy.community)
    _locals = locals()

    wrapper_start = "def notify(policy, action, users):\r\n"

    wrapper_end = "\r\nnotify(policy, action, users)"

    exec_code(policy.notify, wrapper_start, wrapper_end, None, _locals)

def pass_policy(policy, action):
    from policyengine.models import CommunityUser

    users = CommunityUser.objects.filter(community=policy.community)
    _locals = locals()

    wrapper_start = "def success(policy, action, users):\r\n"

    wrapper_end = "\r\nsuccess(policy, action, users)"

    logger.info('policy passed: ' + str(policy.name))
    exec_code(policy.success, wrapper_start, wrapper_end, None, _locals)

def fail_policy(policy, action):
    from policyengine.models import CommunityUser

    users = CommunityUser.objects.filter(community=policy.community)
    _locals = locals()

    wrapper_start = "def fail(policy, action, users):\r\n"

    wrapper_end = "\r\nfail(policy, action, users)"

    logger.info('policy failed: ' + str(policy.name))
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
    from policyengine.models import CommunityRole, PolicykitAddRole, PolicykitEditRole

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    if data['operation'] == 'Add':
        action = PolicykitAddRole()
    elif data['operation'] == 'Change':
        action = PolicykitEditRole()
        action.role = CommunityRole.objects.filter(name=html.unescape(data['name']))[0]
    else:
        return HttpResponseBadRequest()

    action.community = user.community
    action.initiator = user
    action.name = data['role_name']
    action.description = data['description']
    action.save()
    action.permissions.set(Permission.objects.filter(name__in=data['permissions']))
    action.ready = True
    action.save()

    return HttpResponse()

@csrf_exempt
def role_action_users(request):
    from policyengine.models import CommunityRole, CommunityUser, PolicykitAddUserRole, PolicykitRemoveUserRole

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    if data['operation'] == 'Add':
        action = PolicykitAddUserRole()
    elif data['operation'] == 'Remove':
        action = PolicykitRemoveUserRole()
    else:
        return HttpResponseBadRequest()

    action.community = user.community
    action.initiator = user
    action.role = CommunityRole.objects.filter(name=data['role'])[0]
    logger.info('first save')
    action.save()
    action.users.set(CommunityUser.objects.filter(username=data['user']))
    action.ready = True
    logger.info('second save')
    action.save()

    return HttpResponse()

@csrf_exempt
def role_action_remove(request):
    from policyengine.models import CommunityRole, PolicykitDeleteRole

    data = json.loads(request.body)
    user = get_user(request)

    action = PolicykitDeleteRole()
    action.community = user.community
    action.initiator = user
    action.role = CommunityRole.objects.get(name=data['role'])
    action.save()

    return HttpResponse()

@csrf_exempt
def document_action_save(request):
    from policyengine.models import CommunityDoc, PolicykitAddCommunityDoc, PolicykitChangeCommunityDoc

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    if data['operation'] == 'Add':
        action = PolicykitAddCommunityDoc()
    elif data['operation'] == 'Change':
        action = PolicykitChangeCommunityDoc()
        action.doc = CommunityDoc.objects.filter(id=data['doc'])[0]
    else:
        return HttpResponseBadRequest()

    action.community = user.community
    action.initiator = user
    action.name = data['name']
    action.text = data['text']
    action.save()

    return HttpResponse()

@csrf_exempt
def document_action_remove(request):
    from policyengine.models import CommunityDoc, PolicykitDeleteCommunityDoc

    data = json.loads(request.body)
    user = get_user(request)

    action = PolicykitDeleteCommunityDoc()
    action.community = user.community
    action.initiator = user
    action.doc = CommunityDoc.objects.get(id=data['doc'])
    action.save()

    return HttpResponse()
