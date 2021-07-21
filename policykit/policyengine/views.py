from django.conf import settings
from actstream import action as actstream_action
from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.http.response import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.forms import modelform_factory
from actstream.models import Action
from policyengine.filter import filter_code
from policyengine.linter import _error_check
from policyengine.utils import find_action_cls, get_action_classes, construct_authorize_install_url
from policyengine.integration_data import integration_data
from policykit.settings import SERVER_URL, METAGOV_ENABLED
import integrations.metagov.api as MetagovAPI

import logging
import json
import html

logger = logging.getLogger(__name__)
db_logger = logging.getLogger("db")

def homepage(request):
    return render(request, 'home.html', {})

def authorize_platform(request):
    platform = request.GET.get('platform')
    if not platform or platform != "slack":
        return HttpResponseBadRequest()
    from policyengine.models import Community
    new_community = Community.objects.create()
    url = construct_authorize_install_url(request, integration=platform, community=new_community)
    return HttpResponseRedirect(url)

@login_required(login_url='/login')
def v2(request):
    from policyengine.models import CommunityUser, PlatformAction

    user = get_user(request)
    user.community = user.community
    users = CommunityUser.objects.filter(community=user.community)
    roles = user.community.get_roles()
    docs = user.community.get_documents()
    platform_policies = user.community.get_platform_policies()
    constitution_policies = user.community.get_constitution_policies()

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
        if d.is_active:
            doc_data[d.id] = {
                'name': d.name,
                'text': d.text
            }

    platform_policy_data = {}
    for pp in platform_policies:
        if pp.is_active:
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
        if cp.is_active:
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

    action_log = Action.objects.filter(data__community_id=user.community.id)[:20]
    pending_actions = PlatformAction.objects.filter(community=user.community, proposal__status="proposed")

    return render(request, 'policyadmin/dashboard/index.html', {
        'server_url': SERVER_URL,
        'user': user,
        'users': user_data,
        'roles': role_data,
        'docs': doc_data,
        'platform_policies': platform_policy_data,
        'constitution_policies': constitution_policy_data,
        'action_log': action_log,
        'pending_actions': pending_actions
    })

def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('/login')

@login_required(login_url='/login')
def settings_page(request):
    user = get_user(request)
    community = user.community

    context = {
        'metagov_enabled': settings.METAGOV_ENABLED,
        'server_url': settings.SERVER_URL,
        'user': get_user(request),
    }

    if community.metagov_slug:
        result = MetagovAPI.get_metagov_community(community.metagov_slug)
        context['metagov_server_url'] = settings.METAGOV_URL
        context['metagov_community_slug'] = community.metagov_slug
        enabled_integrations = {}
        for plugin in result["plugins"]:
            integration = plugin["name"]
            if integration not in integration_data.keys():
                logger.warn(f"unsupported integration {integration} is enabled for community {community}")
                continue
        
            # Only include configs if user has privileged metagov config role, since they may contain API Keys
            config_tuples = []
            if user.has_perm("metagov.can_edit_metagov_config"):
                config = plugin["config"]
                for (k,v) in config.items():
                    readable_key = k.replace("_", " ").replace("-", " ").capitalize()
                    config_tuples.append((readable_key, v))
            data = {
                **plugin,
                **integration_data[integration],
                "config": config_tuples
            }
            enabled_integrations[integration] = data

        disabled_integrations = [(k, v) for (k,v) in integration_data.items() if k not in enabled_integrations.keys()]

        # FIXME(#384) support multi-platform communities. Here we're hiding slack from the "Add Integrations" dropdown,
        # because we don't have support for multiple CommunityPlatforms connected to one Community.
        disabled_integrations_mod = [(k, v) for (k,v) in disabled_integrations if k not in ["slack"]]

        context["enabled_integrations"] = enabled_integrations.items()
        context["disabled_integrations"] = disabled_integrations_mod

    return render(request, 'policyadmin/dashboard/settings.html', context)

@login_required(login_url="/login")
@csrf_exempt
def add_integration(request):
    """
    This view renders a form for enabling an integration, OR initiates an oauth install flow.
    """
    integration = request.GET.get("integration")
    user = get_user(request)
    community = user.community
    metadata = MetagovAPI.get_plugin_metadata(integration)

    if metadata["auth_type"] == "oauth":
        url = construct_authorize_install_url(request, integration=integration, community=community)
        return HttpResponseRedirect(url)

    context = {
        "integration": integration,
        "metadata": metadata,
        "metadata_string": json.dumps(metadata),
        "additional_data": integration_data[integration]
    }
    return render(request, 'policyadmin/dashboard/integration_settings.html', context)


@login_required(login_url="/login")
@csrf_exempt
def enable_integration(request):
    """
    API Endpoint to enable a Metagov plugin (called on config form submission from JS)
    """
    name = request.GET.get("name") # name of the plugin
    user = get_user(request)
    community = user.community

    if not user.has_perm("metagov.can_edit_metagov_config"):
        return HttpResponseForbidden()

    assert name is not None
    config = json.loads(request.body)
    logger.warn(f"Making request to enable {name} with config {config}")
    res = MetagovAPI.enable_plugin(community.metagov_slug, name, config)
    logger.debug(res)
    return JsonResponse(res, safe=False)

@login_required(login_url="/login")
@csrf_exempt
def disable_integration(request):
    """
    API Endpoint to disable a Metagov plugin (navigated to from Settings page)
    """
    # name of the plugin
    name = request.GET.get("name")
    # id of the plugin (for disabling only)
    id = request.GET.get("id")
    assert id is not None and name is not None

    user = get_user(request)
    community = user.community

    if not user.has_perm("metagov.can_edit_metagov_config"):
        logger.error(f"User {user} does not have permission to disable plugin.")
        return redirect("/main/settings?error=not_permitted")

    # hack: disallow disabling the plugin if the user is logged in with it
    if community.platform == name:
        return redirect("/main/settings?error=not_permitted")

    logger.debug(f"Deleting plugin {name} {id}")
    MetagovAPI.delete_plugin(name=name, id=id)
    return redirect("/main/settings")

@login_required(login_url='/login')
def editor(request):
    from policyengine.models import PlatformPolicy, ConstitutionPolicy

    type = request.GET.get('type')
    operation = request.GET.get('operation')
    policy_id = request.GET.get('policy')

    data = {
        'server_url': SERVER_URL,
        'user': get_user(request),
        'type': type,
        'operation': operation
    }

    if policy_id:
        policy = None
        if type == 'Platform':
            policy = PlatformPolicy.objects.filter(id=policy_id)[0]
        elif type == 'Constitution':
            policy = ConstitutionPolicy.objects.filter(id=policy_id)[0]
        else:
            return HttpResponseBadRequest()

        data['policy'] = policy_id
        data['name'] = policy.name
        data['description'] = policy.description
        data['filter'] = policy.filter
        data['initialize'] = policy.initialize
        data['check'] = policy.check
        data['notify'] = policy.notify
        data['success'] = policy.success
        data['fail'] = policy.fail

    return render(request, 'policyadmin/dashboard/editor.html', data)

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
    user = get_user(request)
    policies = None
    type = request.GET.get('type')
    operation = request.GET.get('operation')

    show_active_policies = True
    if operation == 'Recover':
        show_active_policies = False

    if type == 'Platform':
        policies = user.community.get_platform_policies().filter(is_active=show_active_policies)
    elif type == 'Constitution':
        policies = user.community.get_constitution_policies().filter(is_active=show_active_policies)
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
    user = get_user(request)
    operation = request.GET.get('operation')

    show_active_documents = True
    if operation == 'Recover':
        show_active_documents = False

    documents = user.community.get_documents().filter(is_active=show_active_documents)

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
    app_names = [user.community.platform] # TODO: show actions for other connected platforms
    actions = [(app_name, get_action_classes(app_name)) for app_name in app_names]
    return render(request, 'policyadmin/dashboard/actions.html', {
        'server_url': SERVER_URL,
        'user': get_user(request),
        'actions': actions
    })

@login_required(login_url='/login')
def propose_action(request, app_name, codename):
    cls = find_action_cls(app_name, codename)
    if not cls:
        return HttpResponseBadRequest()

    from policyengine.models import PlatformActionForm

    ActionForm = modelform_factory(
        cls,
        form=PlatformActionForm,
        fields=getattr(cls, "EXECUTE_PARAMETERS", "__all__"),
        localized_fields="__all__"
    )

    new_action = None
    if request.method == 'POST':
        form = ActionForm(request.POST, request.FILES)
        if form.is_valid():
            new_action = form.save(commit=False)
            new_action.initiator = request.user
            new_action.community = request.user.community
            new_action.save()
    else:
        form = ActionForm()
    return render(
        request,
        "policyadmin/dashboard/action_proposer.html",
        {
            "server_url": SERVER_URL,
            "user": get_user(request),
            "form": form,
            "app_name": app_name,
            "codename": codename,
            "action": new_action
        },
    )

def evaluation_logger(policy, action, level="DEBUG"):
    """
    Get a logging function that logs to the database. Logs are visible to the community members at /logs.
    """
    level_num = getattr(logging, level)
    def log(msg):
        message = f"[{action} ({action.pk})][{policy} ({policy.pk})] {msg}"
        db_logger.log(level_num, message, {"community": policy.community})
        logger.log(level_num, message)
    return log

def exec_code(code, wrapperStart, wrapperEnd, globals=None, locals=None):
    """
    errors = filter_code(code)
    if len(errors) > 0:
        logger.exception('Got exception in exec_code:')
        raise Exception(f"Filter errors: {errors}")
    """

    lines = ['  ' + item for item in code.splitlines()]
    code = wrapperStart + '\r\n'.join(lines) + wrapperEnd

    try:
        exec(code, globals, locals)
    except Exception as e:
        logger.exception('Got exception in exec_code:')
        raise

def filter_policy(policy, action, metagov=None):
    from policyengine.models import CommunityUser

    users = CommunityUser.objects.filter(community=policy.community)
    debug = evaluation_logger(policy, action)
    _locals = locals()

    wrapper_start = "def filter(policy, action, users, debug, metagov):\r\n"

    wrapper_end = "\r\nfilter_pass = filter(policy, action, users, debug, metagov)"

    exec_code(policy.filter, wrapper_start, wrapper_end, None, _locals)

    if _locals.get('filter_pass'):
        return _locals['filter_pass']
    else:
        return False

def initialize_policy(policy, action, metagov=None):
    from policyengine.models import Proposal, CommunityUser, BooleanVote, NumberVote

    users = CommunityUser.objects.filter(community=policy.community)
    debug = evaluation_logger(policy, action)

    _locals = locals()
    _globals = globals()

    wrapper_start = "def initialize(policy, action, users, debug, metagov):\r\n"

    wrapper_end = "\r\ninitialize(policy, action, users, debug, metagov)"

    exec_code(policy.initialize, wrapper_start, wrapper_end, None, _locals)

def check_policy(policy, action, metagov=None):
    from policyengine.models import Proposal, CommunityUser, BooleanVote, NumberVote

    users = CommunityUser.objects.filter(community=policy.community)
    boolean_votes = BooleanVote.objects.filter(proposal=action.proposal)
    number_votes = NumberVote.objects.filter(proposal=action.proposal)
    debug = evaluation_logger(policy, action)

    _locals = locals()

    wrapper_start = "def check(policy, action, metagov, users, boolean_votes, number_votes, debug):\r\n"
    wrapper_start += "  PASSED = 'passed'\r\n  FAILED = 'failed'\r\n  PROPOSED = 'proposed'\r\n"

    wrapper_end = "\r\npolicy_pass = check(policy, action, metagov, users, boolean_votes, number_votes, debug)"

    exec_code(policy.check, wrapper_start, wrapper_end, None, _locals)

    if _locals.get('policy_pass'):
        return _locals['policy_pass']
    else:
        return Proposal.PROPOSED

def notify_policy(policy, action, metagov=None):
    from policyengine.models import CommunityUser

    users = CommunityUser.objects.filter(community=policy.community)
    debug = evaluation_logger(policy, action)
    _locals = locals()

    wrapper_start = "def notify(policy, action, users, debug, metagov):\r\n"

    wrapper_end = "\r\nnotify(policy, action, users, debug, metagov)"

    exec_code(policy.notify, wrapper_start, wrapper_end, None, _locals)

def pass_policy(policy, action, metagov=None):
    from policyengine.models import CommunityUser

    users = CommunityUser.objects.filter(community=policy.community)
    debug = evaluation_logger(policy, action)
    _locals = locals()

    wrapper_start = "def success(policy, action, users, debug, metagov):\r\n"

    wrapper_end = "\r\nsuccess(policy, action, users, debug, metagov)"

    exec_code(policy.success, wrapper_start, wrapper_end, None, _locals)

def fail_policy(policy, action, metagov=None):
    from policyengine.models import CommunityUser

    users = CommunityUser.objects.filter(community=policy.community)
    debug = evaluation_logger(policy, action)
    _locals = locals()

    wrapper_start = "def fail(policy, action, users, debug, metagov):\r\n"

    wrapper_end = "\r\nfail(policy, action, users, debug, metagov)"

    exec_code(policy.fail, wrapper_start, wrapper_end, None, _locals)

# TODO(https://github.com/amyxzhang/policykit/issues/342) remove this
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
    from policyengine.models import StarterKit, PlatformPolicy, ConstitutionPolicy, CommunityRole, CommunityUser, Proposal, CommunityPlatform
    from django.contrib.auth.models import Permission

    starterkit_name = request.POST['starterkit']
    community_name = request.POST['community_name']
    creator_token = request.POST['creator_token']
    platform = request.POST['platform']

    starter_kit = StarterKit.objects.get(name=starterkit_name, platform=platform)

    community = CommunityPlatform.objects.get(community_name=community_name)
    starter_kit.init_kit(community, creator_token)

    logger.info('starterkit initialized')

    response = redirect('/login?success=true')
    return response

@csrf_exempt
def error_check(request):
    """
    Takes a request object containing Python code data. Calls _error_check(code)
    to check provided Python code for errors.
    Returns a JSON response containing the output and errors from linting.
    """
    data = json.loads(request.body)
    code = data['code']
    function_name = data['function_name']
    errors = _error_check(code, function_name)
    return JsonResponse({'errors': errors})

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
def policy_action_recover(request):
    from policyengine.models import PlatformPolicy, ConstitutionPolicy, PolicykitRecoverConstitutionPolicy, PolicykitRecoverPlatformPolicy

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    if data['type'] == 'Constitution':
        action = PolicykitRecoverConstitutionPolicy()
        action.constitution_policy = ConstitutionPolicy.objects.get(id=data['policy'])
    elif data['type'] == 'Platform':
        action = PolicykitRecoverPlatformPolicy()
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
    action.save()
    action.users.set(CommunityUser.objects.filter(username=data['user']))
    action.ready = True
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

@csrf_exempt
def document_action_recover(request):
    from policyengine.models import CommunityDoc, PolicykitRecoverCommunityDoc

    data = json.loads(request.body)
    user = get_user(request)

    action = PolicykitRecoverCommunityDoc()
    action.community = user.community
    action.initiator = user
    action.doc = CommunityDoc.objects.get(id=data['doc'])
    action.save()

    return HttpResponse()

def govern_action(action, is_first_evaluation: bool):
    """
    Govern platform and constitution actions:
    - If the initiator has "can execute" permission, execute the action and mark it as "passed."
    - Otherwise, try executing the relevant policies. Stop at the first policy that passes the `filter` step.

    This can be run repeatedly to check proposed actions.
    """
    from policyengine.models import PlatformAction, PlatformActionBundle, ConstitutionAction, ConstitutionActionBundle

    #if they have execute permission, skip all policies
    if action.initiator.has_perm(action._meta.app_label + '.can_execute_' + action.action_codename):
        action.execute()
        action.pass_action()
    else:
        policies = None
        if isinstance(action, PlatformAction) or isinstance(action, PlatformActionBundle):
            policies = action.community.get_platform_policies().filter(is_active=True)
        elif isinstance(action, ConstitutionAction) or isinstance(action, ConstitutionActionBundle):
            policies = action.community.get_constitution_policies().filter(is_active=True)
        else:
            raise Exception("govern_action: unrecognized action")

        for policy in policies:
            # Execute the most recently updated policy that passes filter()
            was_executed = execute_policy(policy, action, is_first_evaluation=is_first_evaluation)
            if was_executed:
                break


def execute_policy(policy, action, is_first_evaluation: bool):
    """
    Execute policy for given action. This can be run repeatedly to check proposed actions.
    Return 'True' if action passed the filter, 'False' otherwise.
    """

    try:
        return _execute_policy(policy, action, is_first_evaluation)
    except Exception as e:
        # Log unhandled exception to the db, so policy author can view it in the UI.
        error = evaluation_logger(policy=policy, action=action, level="ERROR")
        error("Exception: " + str(e))

        # If there was an exception, treat it as if the action didn't pass this policy's filter.
        # This means the action will fall through to the next policy (which might be 'all actions pass' or 'all actions fail' for example)
        # Note: there might be side-effects from a partial execution that can't be undone!
        return False

def _execute_policy(policy, action, is_first_evaluation: bool):
    debug = evaluation_logger(policy, action)

    filter_result = filter_policy(policy, action, metagov=None)
    debug(f"Filter returned {filter_result}")
    if not filter_result:
        return False

    from policyengine.models import Proposal, ConstitutionAction, PlatformAction

    optional_args = {}
    if METAGOV_ENABLED:
        from integrations.metagov.library import Metagov

        optional_args["metagov"] = Metagov(policy, action)

    # If policy is being evaluated for the first time, initialize it
    if is_first_evaluation:
        debug(f"Initializing")
        # run "initialize" block of policy
        initialize_policy(policy, action, **optional_args)

    # Run "check" block of policy
    check_result = check_policy(policy, action, **optional_args)
    debug(f"Check returned {check_result}")

    if check_result == Proposal.PASSED:
        # run "pass" block of policy
        pass_policy(policy, action, **optional_args)
        debug(f"Executed pass block of policy")
        # mark action proposal as 'passed'
        action.pass_action()
        assert action.proposal.status == Proposal.PASSED

        # EXECUTE the action if....
        # it is a PlatformAction that was proposed in the PolicyKit UI
        if issubclass(type(action), PlatformAction) and not action.community_origin:
            action.execute()
        # it is a constitution action
        elif issubclass(type(action), ConstitutionAction):
            action.execute()

        if METAGOV_ENABLED:
            # Close pending process if exists (does nothing if process was already closed)
            optional_args["metagov"].close_process()
            action.proposal.close_governance_process()

    if check_result == Proposal.FAILED:
        # run "fail" block of policy
        fail_policy(policy, action, **optional_args)
        debug(f"Executed fail block of policy")
        # mark action proposal as 'failed'
        action.fail_action()
        assert action.proposal.status == Proposal.FAILED

        if METAGOV_ENABLED:
            # Close pending process if exists (does nothing if process was already closed)
            optional_args["metagov"].close_process()
            action.proposal.close_governance_process()

    # Revert the action if necessary
    should_revert = is_first_evaluation and \
        check_result in [Proposal.PROPOSED, Proposal.FAILED] and \
        issubclass(type(action), PlatformAction) and \
        action.community_origin

    if should_revert:
        debug(f"Reverting")
        action.revert()

    # If this action is moving into pending state for the first time, run the Notify block (to start a vote, maybe)
    if check_result == Proposal.PROPOSED and is_first_evaluation:
        actstream_action.send(action, verb='was proposed', community_id=action.community.id, action_codename=action.action_codename)
        # Run "notify" block of policy
        debug(f"Notifying")
        notify_policy(policy, action, **optional_args)

    return True
