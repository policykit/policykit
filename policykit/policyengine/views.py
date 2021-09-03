from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Permission
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.http.response import HttpResponseForbidden, HttpResponseNotFound, HttpResponseServerError
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.forms import modelform_factory
from actstream.models import Action
from policyengine.filter import filter_code
from policyengine.linter import _error_check
import policyengine.utils as Utils
from policyengine.integration_data import integration_data
from policykit.settings import SERVER_URL
import integrations.metagov.api as MetagovAPI

import logging
import json
import html
import os

logger = logging.getLogger(__name__)

DASHBOARD_MAX_USERS = 50
DASHBOARD_MAX_ACTIONS = 20


def homepage(request):
    return render(request, 'home.html', {})

def authorize_platform(request):
    platform = request.GET.get('platform')
    if not platform or platform != "slack":
        return HttpResponseBadRequest()
    url = Utils.construct_authorize_install_url(request, integration=platform)
    return HttpResponseRedirect(url)

@login_required(login_url='/login')
def v2(request):
    from policyengine.models import CommunityUser, Proposal, CommunityPlatform

    user = get_user(request)
    community = user.community.community
    users = CommunityUser.objects.filter(community__community=community)[:DASHBOARD_MAX_USERS]

    platform_communities = CommunityPlatform.objects.filter(community=community)
    action_log = Action.objects.filter(data__community_id__in=[cp.pk for cp in platform_communities])[:DASHBOARD_MAX_ACTIONS]

    pending_proposals = Proposal.objects.filter(
        policy__community=community,
        status=Proposal.PROPOSED
    ).order_by("-proposal_time")

    return render(request, 'policyadmin/dashboard/index.html', {
        'server_url': SERVER_URL,
        'user': user,
        'users': users,
        'roles': community.get_roles(),
        'docs': community.get_documents(),
        'platform_policies': community.get_platform_policies(),
        'constitution_policies': community.get_constitution_policies(),
        'trigger_policies': community.get_trigger_policies(),
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
        url = Utils.construct_authorize_install_url(request, integration=integration, community=community)
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
    kind = request.GET.get('type', "platform").lower()
    operation = request.GET.get('operation', "Add")
    policy_id = request.GET.get('policy')

    user = get_user(request)
    community = user.community.community

    from policyengine.models import PolicyActionKind
    if kind not in [PolicyActionKind.PLATFORM, PolicyActionKind.CONSTITUTION, PolicyActionKind.TRIGGER]:
        return HttpResponseNotFound()

    # which action types to show in the dropdown
    actions = Utils.get_action_types(community, kinds=[kind])

    data = {
        'server_url': SERVER_URL,
        'user': get_user(request),
        'type': type,
        'operation': operation,
        'actions': actions.items()
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
        data['action_types'] = list(policy.action_types.all().values_list('codename', flat=True))

    return render(request, 'policyadmin/dashboard/editor.html', data)

@login_required(login_url='/login')
def selectrole(request):
    from policyengine.models import CommunityRole

    user = get_user(request)
    operation = request.GET.get('operation')

    roles = user.community.community.get_roles()

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

    community = user.community.community
    roles = community.get_roles()
    users = CommunityUser.objects.filter(community__community=community).order_by('readable_name', 'username')

    return render(request, 'policyadmin/dashboard/role_users.html', {
        'server_url': SERVER_URL,
        'roles': roles,
        'users': users,
        'operation': operation
    })

@login_required(login_url='/login')
def roleeditor(request):
    from policyengine.models import CommunityRole, CommunityPlatform

    user = get_user(request)
    operation = request.GET.get('operation')
    role_name = request.GET.get('role')

    # List permissions for all CommunityPlatforms connected to this community
    platforms = [c.platform for c in CommunityPlatform.objects.filter(community=user.community.community)]
    permissions = Utils.get_all_permissions(platforms).values_list('name', flat=True)

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
        policies = user.community.community.get_platform_policies().filter(is_active=show_active_policies)
    elif type == 'Constitution':
        policies = user.community.community.get_constitution_policies().filter(is_active=show_active_policies)
    elif type == 'Trigger':
        policies = user.community.community.get_trigger_policies().filter(is_active=show_active_policies)
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

    documents = user.community.community.get_documents().filter(is_active=show_active_documents)

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
    community = user.community.community

    from policyengine.models import PolicyActionKind
    actions = Utils.get_action_types(community, kinds=[PolicyActionKind.PLATFORM])
    return render(request, 'policyadmin/dashboard/actions.html', {
        'server_url': SERVER_URL,
        'user': get_user(request),
        'actions': actions.items()
    })

@login_required(login_url='/login')
def propose_action(request, app_name, codename):
    cls = Utils.find_action_cls(app_name, codename)
    if not cls:
        return HttpResponseBadRequest()

    from policyengine.models import GovernableActionForm, Proposal

    ActionForm = modelform_factory(
        cls,
        form=GovernableActionForm,
        fields=getattr(cls, "EXECUTE_PARAMETERS", "__all__"),
        localized_fields="__all__"
    )

    new_action = None
    proposal = None
    if request.method == 'POST':
        form = ActionForm(request.POST, request.FILES)
        if form.is_valid():
            new_action = form.save(commit=False)
            if request.user.community.platform == app_name:
                # user is logged in with the same platform that this action is for
                new_action.initiator = request.user
                new_action.community = request.user.community
            else:
                # user is logged in with a different platform. no initiator.
                new_action.community = request.user.community.community.get_platform_community(app_name)
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
    from policyengine.models import Community

    post_data = json.loads(request.body)
    starterkit = post_data["starterkit"]
    community = Community.objects.get(pk=post_data["community_id"])

    logger.debug(f'Initializing community {community} with starter kit {starterkit}...')
    cur_path = os.path.abspath(os.path.dirname(__file__))
    starter_kit_path = os.path.join(cur_path, f'../starterkits/{starterkit}.txt')
    f = open(starter_kit_path)
    kit_data = json.loads(f.read())
    f.close()

    Utils.initialize_starterkit_inner(community, kit_data, creator_token=post_data.get("creator_token"))

    return JsonResponse({"ok": True})

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
    from policyengine.models import Policy
    from constitution.models import (PolicykitAddConstitutionPolicy,
        PolicykitAddTriggerPolicy, PolicykitChangeTriggerPolicy, PolicykitAddPlatformPolicy,
        PolicykitChangeConstitutionPolicy, PolicykitChangePlatformPolicy, ActionType, PolicyActionKind)

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    operation = data['operation']
    kind = data['type'].lower()

    if kind not in [PolicyActionKind.PLATFORM, PolicyActionKind.CONSTITUTION, PolicyActionKind.TRIGGER]:
        return HttpResponseNotFound()

    if operation == "Add":
        if kind == PolicyActionKind.CONSTITUTION:
            action = PolicykitAddConstitutionPolicy()
        elif kind == PolicyActionKind.PLATFORM:
            action = PolicykitAddPlatformPolicy()
        elif kind == PolicyActionKind.TRIGGER:
            action = PolicykitAddTriggerPolicy()
        action.is_bundled = data.get('is_bundled', False)
    
    elif operation == "Change":
        if kind == PolicyActionKind.CONSTITUTION:
            action = PolicykitChangeConstitutionPolicy()
        elif kind == PolicyActionKind.PLATFORM:
            action = PolicykitChangePlatformPolicy()
        elif kind == PolicyActionKind.TRIGGER:
            action = PolicykitChangeTriggerPolicy()
        
        try:
            action.policy = Policy.objects.get(pk=data['policy'])
        except Policy.DoesNotExist:
            return HttpResponseNotFound()

    else:
        return HttpResponseNotFound()

    action.community = user.constitution_community
    action.initiator = user
    action.name = data['name']
    action.description = data.get('description', None)
    action.filter = data['filter']
    action.initialize = data['initialize']
    action.check = data['check']
    action.notify = data['notify']
    action.success = data['success']
    action.fail = data['fail']

    if not data["name"]:
        return HttpResponseBadRequest("Enter a name.")
    if len(data["action_types"]) < 1:
        if action and hasattr(action, "policy") and action.policy.action_types.count() == 0 and kind != PolicyActionKind.TRIGGER:
            pass # the policy already had no action types, so it's a base policy. ignore
        else:
            return HttpResponseBadRequest("Select one or more action types.")

    try:
        action.save(evaluate_action=False)
    except Exception as e:
        logger.error(f"Error saving policy: {e}")
        return HttpResponseServerError()

    action_types = [ActionType.objects.get_or_create(codename=codename)[0] for codename in data["action_types"]]
    action.action_types.set(action_types)

    try:
        action.save(evaluate_action=True)
    except Exception as e:
        logger.error(f"Error evaluating policy: {e}")
        return HttpResponseServerError()

    return HttpResponse()

@csrf_exempt
def policy_action_remove(request):
    from policyengine.models import Policy
    from constitution.models import PolicykitRemoveConstitutionPolicy, PolicykitRemovePlatformPolicy

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    try:
        policy = Policy.objects.get(pk=data['policy'])
    except Policy.DoesNotExist:
        return HttpResponseNotFound()
    if policy.kind == Policy.CONSTITUTION:
        action = PolicykitRemoveConstitutionPolicy()
        action.policy = policy
    elif policy.kind == Policy.PLATFORM:
        action = PolicykitRemovePlatformPolicy()
        action.policy = policy
    else:
        return HttpResponseBadRequest()

    action.community = user.constitution_community
    action.initiator = user
    action.save()

    return HttpResponse()

@csrf_exempt
def policy_action_recover(request):
    from policyengine.models import Policy
    from constitution.models import PolicykitRecoverConstitutionPolicy, PolicykitRecoverPlatformPolicy

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    try:
        policy = Policy.objects.get(pk=data['policy'])
    except Policy.DoesNotExist:
        return HttpResponseNotFound()
    if policy.kind == Policy.CONSTITUTION:
        action = PolicykitRecoverConstitutionPolicy()
        action.policy = policy
    elif policy.kind == Policy.PLATFORM:
        action = PolicykitRecoverPlatformPolicy()
        action.policy = policy
    else:
        return HttpResponseBadRequest()

    action.community = user.constitution_community
    action.initiator = user
    action.save()

    return HttpResponse()


@csrf_exempt
def role_action_save(request):
    from policyengine.models import CommunityRole
    from constitution.models import PolicykitAddRole, PolicykitEditRole

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

    action.community = user.constitution_community
    action.initiator = user
    action.name = data['role_name']
    action.description = data['description']
    action.save(evaluate_action=False)
    action.permissions.set(Permission.objects.filter(name__in=data['permissions']))
    action.save(evaluate_action=True)

    return HttpResponse()

@csrf_exempt
def role_action_users(request):
    from policyengine.models import CommunityRole, CommunityUser
    from constitution.models import PolicykitAddUserRole, PolicykitRemoveUserRole

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    if data['operation'] == 'Add':
        action = PolicykitAddUserRole()
    elif data['operation'] == 'Remove':
        action = PolicykitRemoveUserRole()
    else:
        return HttpResponseBadRequest()

    action.community = user.constitution_community
    action.initiator = user
    action.role = CommunityRole.objects.filter(name=data['role'])[0]
    action.save(evaluate_action=False)
    action.users.set(CommunityUser.objects.filter(username=data['user']))
    action.save(evaluate_action=True)

    return HttpResponse()

@csrf_exempt
def role_action_remove(request):
    from policyengine.models import CommunityRole
    from constitution.models import PolicykitDeleteRole

    data = json.loads(request.body)
    user = get_user(request)

    action = PolicykitDeleteRole()
    action.community = user.constitution_community
    action.initiator = user
    action.role = CommunityRole.objects.get(name=data['role'])
    action.save()

    return HttpResponse()

@csrf_exempt
def document_action_save(request):
    from policyengine.models import CommunityDoc
    from constitution.models import PolicykitAddCommunityDoc, PolicykitChangeCommunityDoc

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

    action.community = user.constitution_community
    action.initiator = user
    action.name = data['name']
    action.text = data['text']
    action.save()

    return HttpResponse()

@csrf_exempt
def document_action_remove(request):
    from policyengine.models import CommunityDoc
    from constitution.models import PolicykitDeleteCommunityDoc

    data = json.loads(request.body)
    user = get_user(request)

    action = PolicykitDeleteCommunityDoc()
    action.community = user.constitution_community
    action.initiator = user
    action.doc = CommunityDoc.objects.get(id=data['doc'])
    action.save()

    return HttpResponse()

@csrf_exempt
def document_action_recover(request):
    from policyengine.models import CommunityDoc
    from constitution.models import PolicykitRecoverCommunityDoc

    data = json.loads(request.body)
    user = get_user(request)

    action = PolicykitRecoverCommunityDoc()
    action.community = user.constitution_community
    action.initiator = user
    action.doc = CommunityDoc.objects.get(id=data['doc'])
    action.save()

    return HttpResponse()
