from django.conf import settings
from django.contrib.auth import authenticate, login, get_user
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Permission
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.http.response import HttpResponseServerError
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.forms import modelform_factory
from actstream.models import Action
from policyengine.filter import filter_code
from policyengine.linter import _error_check
import policyengine.utils as Utils
from policyengine.utils import INTEGRATION_ADMIN_ROLE_NAME
from policyengine.integration_data import integration_data
from policyengine.metagov_app import metagov, metagov_handler

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
    """
    Authorize endpoint for installing & logging into Metagov-backed platforms
    """
    platform = request.GET.get('platform')
    req_type = request.GET.get('type', 'app')

    # User logins redirect to `/authenticate_user` endpoint for django authentication.
    # App installs redirect to `/<platform>/install` endpoint for install completion (e.g. creating the SlackCommunity).
    redirect_uri = f"{settings.SERVER_URL}/authenticate_user" if req_type == "user" else f"{settings.SERVER_URL}/{platform}/install"

    # This returns a redirect to the platform's oauth server (e.g.  https://slack.com/oauth/v2/authorize)
    # which will prompt the user to confirm. After that, it will navigate to the specified redirect_uri.
    return metagov_handler.handle_oauth_authorize(
        request,
        plugin_name=platform,
        redirect_uri=redirect_uri,
        type=req_type
    )


def authenticate_user(request):
    # Django chooses which auth backend to use
    user = authenticate(request)
    if user:
        login(request, user)
        return redirect("/main")

    # TODO: better error messages
    return redirect("/login?error=login_failed")


def logout(request):
    from django.contrib.auth import logout
    logout(request)
    return redirect('/login')

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


@login_required(login_url='/login')
def settings_page(request):
    user = get_user(request)
    community = user.community

    context = {'user': user}

    if community.metagov_slug:
        mg_community = metagov.get_community(community.metagov_slug)
        context['metagov_community_slug'] = community.metagov_slug
        enabled_integrations = {}
        for plugin in mg_community.plugins.all():
            integration = plugin.name
            if integration not in integration_data.keys():
                logger.warn(f"unsupported integration {integration} is enabled for community {community}")
                continue

            # Only include configs if user has permission, since they may contain API Keys
            config_tuples = []
            if user.has_role(INTEGRATION_ADMIN_ROLE_NAME):
                for (k,v) in plugin.config.items():
                    readable_key = k.replace("_", " ").replace("-", " ").capitalize()
                    config_tuples.append((readable_key, v))

            # Add additional data about the integration, like description and webhook URL
            additional_data = integration_data[integration]
            if additional_data.get("webhook_instructions"):
                additional_data["webhook_url"] = f"{settings.SERVER_URL}/api/hooks/{plugin.name}/{plugin.community.slug}"
            
            enabled_integrations[integration] = {**plugin.serialize(), **additional_data, "config": config_tuples}

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

    metadata = metagov.get_plugin_metadata(integration)

    if metadata["auth_type"] == "oauth":
        return metagov_handler.handle_oauth_authorize(
            request,
            plugin_name=integration,
            redirect_uri=f"{settings.SERVER_URL}/{integration}/install",
            community_slug=community.metagov_slug,
        )


    context = {
        "integration": integration,
        "metadata": metadata,
        "metadata_string": json.dumps(metadata),
        "additional_data": integration_data[integration]
    }
    return render(request, 'policyadmin/dashboard/integration_settings.html', context)


@login_required(login_url="/login")
@permission_required("constitution.can_add_integration", raise_exception=True)
@csrf_exempt
def enable_integration(request, integration):
    """
    API Endpoint to enable a Metagov plugin (called on config form submission from JS).
    This is the default implementation; platforms with PolicyKit integrations may override it.
    """
    user = get_user(request)
    community = user.community.community

    config = json.loads(request.body)
    logger.debug(f"Enabling {integration} with config {config} for {community}")
    plugin = metagov.get_community(community.metagov_slug).enable_plugin(integration, config)

    # Create the corresponding CommunityPlatform instance
    from django.apps import apps
    cls =  apps.get_app_config(integration).get_model(f"{integration}community")
    team_id = plugin.community_platform_id
    cp,created = cls.objects.get_or_create(
        community=community,
        team_id=team_id,
        defaults={"community_name": team_id}
    )
    logger.debug(f"CommunityPlatform '{cp.platform} {cp}' {'created' if created else 'already exists'}")

    return HttpResponse()


@login_required(login_url="/login")
@permission_required("constitution.can_remove_integration", raise_exception=True)
@csrf_exempt
def disable_integration(request, integration):
    """
    API Endpoint to disable a Metagov plugin (navigated to from Settings page).
    This is only used for plugins that DON'T have a corresponding PolicyKit integration.
    For platforms with integrations (Open Collective, Github, etc) the installation
    is handled by the integration.
    """
    id = int(request.GET.get("id")) # id of the plugin
    user = get_user(request)
    community = user.community.community
    logger.debug(f"Deleting plugin {integration} {id} for community {community}")
    metagov.get_community(community.metagov_slug).disable_plugin(integration, id=id)

    community_platform = community.get_platform_community(name=integration)
    if community_platform:
        community_platform.delete()

    return redirect("/main/settings")


@login_required(login_url='/login')
def editor(request):
    kind = request.GET.get('type', "platform").lower()
    operation = request.GET.get('operation', "Add")
    policy_id = request.GET.get('policy')

    user = get_user(request)
    community = user.community.community

    from policyengine.models import PolicyActionKind, Policy
    if kind not in [PolicyActionKind.PLATFORM, PolicyActionKind.CONSTITUTION, PolicyActionKind.TRIGGER]:
        raise Http404("Policy does not exist")

    policy = None
    if policy_id:
        try:
            policy = Policy.objects.get(id=policy_id, community=user.community.community)
        except Policy.DoesNotExist:
            raise Http404("Policy does not exist")

    # which action types to show in the dropdown
    actions = Utils.get_action_types(community, kinds=[kind])

    # list of autocomplete strings
    action_types = [a.codename for a in policy.action_types.all()] if policy else None
    autocompletes = Utils.get_autocompletes(community, action_types=action_types)

    data = {
        'user': get_user(request),
        'type': kind.capitalize(),
        'operation': operation,
        'actions': actions.items(),
        'autocompletes': json.dumps(autocompletes)
    }

    if policy:
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
        'roles': roles,
        'users': users,
        'operation': operation
    })

@login_required(login_url='/login')
def roleeditor(request):
    from policyengine.models import CommunityRole, CommunityPlatform

    user = get_user(request)
    operation = request.GET.get('operation')
    role_pk = request.GET.get('role')

    # List permissions for all CommunityPlatforms connected to this community
    platforms = [c.platform for c in CommunityPlatform.objects.filter(community=user.community.community)]
    permissions = Utils.get_all_permissions(platforms).values_list('name', flat=True)

    data = {
        'user': user,
        'permissions': list(sorted(permissions)),
        'operation': operation
    }

    if role_pk:
        try:
            role = CommunityRole.objects.get(pk=role_pk, community=user.community.community)
        except CommunityRole.DoesNotExist:
            raise Http404("Role does not exist")
        data['role_name'] = role.role_name
        data['name'] = role.name
        data['description'] = role.description
        currentPermissions = list(role.permissions.filter(name__in=permissions).values_list('name', flat=True))
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
        policies = user.community.community.get_platform_policies(is_active=show_active_policies)
    elif type == 'Constitution':
        policies = user.community.community.get_constitution_policies(is_active=show_active_policies)
    elif type == 'Trigger':
        policies = user.community.community.get_trigger_policies(is_active=show_active_policies)
    else:
        return HttpResponseBadRequest()

    return render(request, 'policyadmin/dashboard/policy_select.html', {
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
        'user': user,
        'operation': operation
    }

    if doc_id:
        try:
            doc = CommunityDoc.objects.get(id=doc_id, community=user.community.community)
        except CommunityDoc.DoesNotExist:
            raise Http404("Document does not exist")

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
        'user': get_user(request),
        'actions': actions.items()
    })

@login_required(login_url='/login')
def propose_action(request, app_name, codename):
    cls = Utils.find_action_cls(codename, app_name)
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

@login_required(login_url='/login')
def get_autocompletes(request):
    user = request.user
    community = user.community.community
    action_types = request.GET.get("action_types").split(",")
    if not action_types or len(action_types) == 1 and not action_types[0]:
        action_types = None
    autocompletes = Utils.get_autocompletes(community, action_types=action_types)
    return JsonResponse({'autocompletes': autocompletes})

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
        raise Http404("Policy does not exist")

    if operation == "Add":
        if kind == PolicyActionKind.CONSTITUTION:
            action = PolicykitAddConstitutionPolicy()
        elif kind == PolicyActionKind.PLATFORM:
            action = PolicykitAddPlatformPolicy()
        elif kind == PolicyActionKind.TRIGGER:
            action = PolicykitAddTriggerPolicy()
        # action.is_bundled = data.get('is_bundled', False)
    
    elif operation == "Change":
        if kind == PolicyActionKind.CONSTITUTION:
            action = PolicykitChangeConstitutionPolicy()
        elif kind == PolicyActionKind.PLATFORM:
            action = PolicykitChangePlatformPolicy()
        elif kind == PolicyActionKind.TRIGGER:
            action = PolicykitChangeTriggerPolicy()
        
        try:
            action.policy = Policy.objects.get(pk=data['policy'], community=user.community.community)
        except Policy.DoesNotExist:
            raise Http404("Policy does not exist")

    else:
        raise Http404("Policy does not exist")

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
    from constitution.models import PolicykitRemoveConstitutionPolicy, PolicykitRemovePlatformPolicy, PolicykitRemoveTriggerPolicy

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    try:
        policy = Policy.objects.get(pk=data['policy'], community=user.community.community)
    except Policy.DoesNotExist:
        raise Http404("Policy does not exist")

    if policy.kind == Policy.CONSTITUTION:
        action = PolicykitRemoveConstitutionPolicy()
    elif policy.kind == Policy.PLATFORM:
        action = PolicykitRemovePlatformPolicy()
    elif policy.kind == Policy.TRIGGER:
        action = PolicykitRemoveTriggerPolicy()
    else:
        return HttpResponseBadRequest()

    action.policy = policy
    action.community = user.constitution_community
    action.initiator = user
    action.save()

    return HttpResponse()

@csrf_exempt
def policy_action_recover(request):
    from policyengine.models import Policy
    from constitution.models import PolicykitRecoverConstitutionPolicy, PolicykitRecoverPlatformPolicy, PolicykitRecoverTriggerPolicy

    data = json.loads(request.body)
    user = get_user(request)

    action = None
    try:
        policy = Policy.objects.get(pk=data['policy'], community=user.community.community)
    except Policy.DoesNotExist:
        raise Http404("Policy does not exist")

    if policy.kind == Policy.CONSTITUTION:
        action = PolicykitRecoverConstitutionPolicy()
    elif policy.kind == Policy.PLATFORM:
        action = PolicykitRecoverPlatformPolicy()
    elif policy.kind == Policy.TRIGGER:
        action = PolicykitRecoverTriggerPolicy()
    else:
        return HttpResponseBadRequest(f"Unrecognized policy kind: {policy.kind}")

    action.policy = policy
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
    try:
        action.role = CommunityRole.objects.get(pk=data['role'], community=user.community.community)
    except CommunityRole.DoesNotExist:
        raise Http404("Role does not exist")
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
        try:
            action.doc = CommunityDoc.objects.get(id=data['doc'], community=user.community.community)
        except CommunityDoc.DoesNotExist:
            raise Http404("Document does not exist")
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
    try:
        action.doc = CommunityDoc.objects.get(id=data['doc'], community=user.community.community)
    except CommunityDoc.DoesNotExist:
        raise Http404("Document does not exist")
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
    try:
        action.doc = CommunityDoc.objects.get(id=data['doc'], community=user.community.community)
    except CommunityDoc.DoesNotExist:
        raise Http404("Document does not exist")
    action.save()

    return HttpResponse()
