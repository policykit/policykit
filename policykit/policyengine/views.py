from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.http.response import HttpResponseForbidden, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.forms import modelform_factory
from actstream.models import Action
from policyengine.filter import filter_code
from policyengine.linter import _error_check
from policyengine.utils import find_action_cls, get_action_classes, construct_authorize_install_url, get_action_content_types
from policyengine.integration_data import integration_data
from policykit.settings import SERVER_URL
import integrations.metagov.api as MetagovAPI

import logging
import json
import html
import os

logger = logging.getLogger(__name__)

def homepage(request):
    return render(request, 'home.html', {})

def authorize_platform(request):
    platform = request.GET.get('platform')
    if not platform or platform != "slack":
        return HttpResponseBadRequest()
    url = construct_authorize_install_url(request, integration=platform)
    return HttpResponseRedirect(url)

@login_required(login_url='/login')
def v2(request):
    from policyengine.models import CommunityUser, Proposal

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
    pending_proposals = Proposal.objects.filter(
        policy__community=user.community,
        status=Proposal.PROPOSED
    ).order_by("-proposal_time")

    return render(request, 'policyadmin/dashboard/index.html', {
        'server_url': SERVER_URL,
        'user': user,
        'users': user_data,
        'roles': role_data,
        'docs': doc_data,
        'platform_policies': platform_policy_data,
        'constitution_policies': constitution_policy_data,
        'action_log': action_log,
        'pending_proposals': pending_proposals
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

        context["enabled_integrations"] = enabled_integrations.items()
        context["disabled_integrations"] = disabled_integrations

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
        return redirect("/main/settings?error=insufficient_permissions")

    # hack: disallow disabling the plugin if the user is logged in with it
    if community.platform == name:
        return redirect("/main/settings?error=cant_delete_current_platform")

    # Temporary: disallow disabling the plugins that have a corresponding PlatformCommunity.
    # We would need to delete the SlackCommunity as well, which we should show a warning for!
    if name == "slack":
        return redirect("/main/settings?error=cant_delete_slack")

    logger.debug(f"Deleting plugin {name} {id}")
    MetagovAPI.delete_plugin(name=name, id=id)
    return redirect("/main/settings")

@login_required(login_url='/login')
def editor(request):
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
        from policyengine.models import Policy
        policy = None
        try:
            policy = Policy.objects.get(id=policy_id)
        except Policy.DoesNotExist:
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

    actions = {}
    for app_name in app_names:
        action_list = []
        for cls in get_action_classes(app_name):
            action_list.append((cls._meta.model_name, cls._meta.verbose_name.title()))
        if action_list:
            actions[app_name] = action_list

    return render(request, 'policyadmin/dashboard/actions.html', {
        'server_url': SERVER_URL,
        'user': get_user(request),
        'actions': actions.items()
    })

@login_required(login_url='/login')
def propose_action(request, app_name, codename):
    cls = find_action_cls(app_name, codename)
    if not cls:
        return HttpResponseBadRequest()

    from policyengine.models import PlatformActionForm, Proposal

    ActionForm = modelform_factory(
        cls,
        form=PlatformActionForm,
        fields=getattr(cls, "EXECUTE_PARAMETERS", "__all__"),
        localized_fields="__all__"
    )

    new_action = None
    proposal = None
    if request.method == 'POST':
        form = ActionForm(request.POST, request.FILES)
        if form.is_valid():
            new_action = form.save(commit=False)
            new_action.initiator = request.user
            new_action.community = request.user.community
            new_action.save()
            proposal = Proposal.objects.filter(action=new_action).first()
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
            "verbose_name": cls._meta.verbose_name.title(),
            "action": new_action,
            "proposal": proposal,
        },
    )


@csrf_exempt
def initialize_starterkit(request):
    """
    Takes a request object containing starter-kit information.
    Initializes the community with the selected starter kit.
    """
    from policyengine.models import Proposal, CommunityPlatform, Policy, CommunityRole, CommunityUser

    post_data = json.loads(request.body)

    logger.debug(f'Initializing with starter kit: {post_data["starterkit"]}')
    cur_path = os.path.abspath(os.path.dirname(__file__))
    starter_kit_path = os.path.join(cur_path, f'../starterkits/{post_data["starterkit"]}.txt')
    f = open(starter_kit_path)

    kit_data = json.loads(f.read())

    # TODO: Community name is not necessarily unique! Should use pk instead.
    community = CommunityPlatform.objects.get(community_name=post_data["community_name"])

    # Initialize platform policies from starter kit
    for policy in kit_data['platform_policies']:
        Policy.objects.create(
            kind=Policy.PLATFORM,
            name=policy['name'],
            description=policy['description'],
            filter=policy['filter'],
            initialize=policy['initialize'],
            check=policy['check'],
            notify=policy['notify'],
            success=policy['success'],
            fail=policy['fail'],
            community=community
        )

    # Initialize constitution policies from starter kit
    for policy in kit_data['constitution_policies']:
        Policy.objects.create(
            kind=Policy.CONSTITUTION,
            name=policy['name'],
            description=policy['description'],
            filter=policy['filter'],
            initialize=policy['initialize'],
            check=policy['check'],
            notify=policy['notify'],
            success=policy['success'],
            fail=policy['fail'],
            community=community
        )

    # Initialize roles from starter kit
    for role in kit_data['roles']:
        r = CommunityRole.objects.create(
            role_name=role['name'],
            name=f"{post_data['platform']}: {community.community_name}: {role['name']}",
            description=role['description'],
            community=community
        )

        if role['is_base_role']:
            old_base_role = community.base_role
            community.base_role = r
            community.save()
            old_base_role.delete()

        # Add PolicyKit-related permissions
        r.permissions.set(Permission.objects.filter(name__in=role['permissions']))

        # Add permissions for each PlatformAction
        action_content_types = get_action_content_types(community.platform)
        if 'view' in role['permission_sets']:
            view_perms = Permission.objects.filter(content_type__in=action_content_types, name__startswith="Can view")
            r.permissions.add(view_perms)
        if 'propose' in role['permission_sets']:
            propose_perms = Permission.objects.get(content_type__in=action_content_types, name__startswith="Can add")
            r.permissions.add(propose_perms)
        if 'execute' in role['permission_sets']:
            execute_perms = Permission.objects.get(content_type__in=action_content_types, name__startswith="Can execute")
            r.permissions.add(execute_perms)

        group = None
        if role['user_group'] == "all":
            group = CommunityUser.objects.filter(community=community)
        elif role['user_group'] == "admins":
            group = CommunityUser.objects.filter(community=community, is_community_admin=True)
        elif role['user_group'] == "nonadmins":
            group = CommunityUser.objects.filter(community=community, is_community_admin=False)
        elif role['user_group'] == "creator":
            group = CommunityUser.objects.filter(community=community, access_token=post_data["creator_token"])

        for user in group:
            r.user_set.add(user)

        r.save()

    f.close()

    redirect_route = request.GET.get("redirect")
    if redirect_route:
        return JsonResponse({'redirect': f"{redirect_route}?success=true"})
    return JsonResponse({'redirect': '/login?success=true'})

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
    from policyengine.models import Policy, PolicykitAddConstitutionPolicy, PolicykitAddPlatformPolicy, PolicykitChangeConstitutionPolicy, PolicykitChangePlatformPolicy

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
        try:
            policy = Policy.objects.get(pk=data['policy'])
        except Policy.DoesNotExist:
            return HttpResponseNotFound()
        action.constitution_policy = policy
    elif data['type'] == 'Platform' and data['operation'] == 'Change':
        action = PolicykitChangePlatformPolicy()
        try:
            policy = Policy.objects.get(pk=data['policy'])
        except Policy.DoesNotExist:
            return HttpResponseNotFound()
        action.platform_policy = policy
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
    try:
        action.save()
    except Exception as e:
        logger.error(f"Error saving policy: {e}")
        return HttpResponseBadRequest()

    return HttpResponse()

@csrf_exempt
def policy_action_remove(request):
    from policyengine.models import Policy, PolicykitRemoveConstitutionPolicy, PolicykitRemovePlatformPolicy

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    try:
        policy = Policy.objects.get(pk=data['policy'])
    except Policy.DoesNotExist:
        return HttpResponseNotFound()
    if policy.kind == Policy.CONSTITUTION:
        action = PolicykitRemoveConstitutionPolicy()
        action.constitution_policy = policy
    elif policy.kind == Policy.PLATFORM:
        action = PolicykitRemovePlatformPolicy()
        action.platform_policy = policy
    else:
        return HttpResponseBadRequest()

    action.community = user.community
    action.initiator = user
    action.save()

    return HttpResponse()

@csrf_exempt
def policy_action_recover(request):
    from policyengine.models import Policy, PolicykitRecoverConstitutionPolicy, PolicykitRecoverPlatformPolicy

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    try:
        policy = Policy.objects.get(pk=data['policy'])
    except Policy.DoesNotExist:
        return HttpResponseNotFound()
    if policy.kind == Policy.CONSTITUTION:
        action = PolicykitRecoverConstitutionPolicy()
        action.constitution_policy = policy
    elif policy.kind == Policy.PLATFORM:
        action = PolicykitRecoverPlatformPolicy()
        action.platform_policy = policy
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
