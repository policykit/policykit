import html
import json
import logging
import os

from actstream.models import Action
import black 
from django.conf import settings
from django.contrib.auth import authenticate, get_user, login
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Permission
from django.forms import modelform_factory
from django.http import (Http404, HttpResponse, HttpResponseBadRequest,
                         JsonResponse)
from django.http.response import HttpResponseServerError
from django.shortcuts import redirect, render

import policyengine.utils as Utils
from policyengine.integration_data import integration_data
from policyengine.linter import _lint_check
from policyengine.metagov_app import metagov, metagov_handler
from policyengine.utils import INTEGRATION_ADMIN_ROLE_NAME

logger = logging.getLogger(__name__)

DASHBOARD_MAX_USERS = 50
DASHBOARD_MAX_ACTIONS = 20
DASHBOARD_BASE = "policyadmin/dashboard/dashboard_base.html"
DASHBOARD_BASE_AJAX = "policyadmin/dashboard/dashboard_base_ajax.html"

def homepage(request):
    """PolicyKit splash page"""
    return render(request, 'home.html', {})

def authorize_platform(request):
    """
    Authorize endpoint for installing & logging into Metagov-backed platforms.
    The "type" parameter indicates whether it is a user login or an installation.
    """
    platform = request.GET.get('platform')
    req_type = request.GET.get('type', 'app')
    redirect_uri = request.GET.get('redirect_uri')

    # By default, user login redirects to `/authenticate_user` endpoint for django authentication.
    # By default, app installtion redirects to `/<platform>/install` endpoint for install completion (e.g. creating the SlackCommunity).
    if redirect_uri is None:
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
    """
    Django authentication endpoint. This gets invoked after the platform oauth flow has successfully completed.
    """
    # Django chooses which auth backend to use (SlackBackend, DiscordBackend, etc)
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

def initialize_starterkit(request):
    """
    Set up starterkit policies and roles for a new community. Gets called when a user selects a starterkit on the init_startkit page
    """
    from policyengine.models import Community

    starterkit_id = request.GET.get("kit")
    community_id = request.session["starterkit_init_community_id"]
    creator_username = request.session["starterkit_init_creator_username"]
    if not community_id:
        raise Http404
    del request.session["starterkit_init_community_id"]
    del request.session["starterkit_init_creator_username"]

    community = Community.objects.get(pk=community_id)

    logger.debug(f'Initializing community {community} with starter kit {starterkit_id}...')
    cur_path = os.path.abspath(os.path.dirname(__file__))
    starter_kit_path = os.path.join(cur_path, f'../starterkits/{starterkit_id}.json')
    f = open(starter_kit_path)
    kit_data = json.loads(f.read())
    f.close()

    try:
        Utils.initialize_starterkit_inner(community, kit_data, creator_username=creator_username)
    except Exception as e:
        logger.error(f"Initializing kit {starterkit_id} raised exception {type(e).__name__} {e}")
        return redirect("/login?error=starterkit_init_failed")

    return redirect("/login?success=true")

@login_required
def onboarding(request):
    from policyengine.models import CommunityUser
    user = get_user(request)
    community = user.community.community

    # List all CommunityUsers across all platforms connected to this community
    users = CommunityUser.objects.filter(community__community=community)

    cur_path = os.path.abspath(os.path.dirname(__file__))
    startkit_path = os.path.join(cur_path, f"../starterkits/onboarding.json")
    startkit = open(startkit_path)
    data = json.loads(startkit.read())

    platform_policies = data.get("platform_policies", [])
    constitution_policies = data.get("constitution_policies", [])
    return render(request, "policyadmin/onboarding.html", {
        'community_members': users,
        'platform_policies': platform_policies,
        'constitution_policies': constitution_policies,
    })

@login_required
def dashboard(request):
    from policyengine.models import CommunityPlatform, CommunityUser, Proposal
    user = get_user(request)
    community = user.community.community

    # List all CommunityUsers across all platforms connected to this community
    users = CommunityUser.objects.filter(community__community=community)[:DASHBOARD_MAX_USERS]

    # List recent actions across all CommunityPlatforms connected to this community
    platform_communities = CommunityPlatform.objects.filter(community=community)
    action_log = Action.objects.filter(data__community_id__in=[cp.pk for cp in platform_communities])[:DASHBOARD_MAX_ACTIONS]

    # List pending proposals for all Policies connected to this community
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


@login_required
def settings_page(request):
    """
    Settings page for enabling/disabling platform integrations.
    """
    user = get_user(request)
    community = user.community

    context = {
        "user": user,
        "enabled_integrations": [],
        "disabled_integrations": []
    }

    if community.metagov_slug:
        enabled_integrations = {}
        # Iterate through all Metagov Plugins enabled for this community
        for plugin in metagov.get_community(community.metagov_slug).plugins.all():
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


        context["enabled_integrations"] = enabled_integrations.items()
        context["disabled_integrations"] = [(k, v) for (k,v) in integration_data.items() if k not in enabled_integrations.keys()]

    return render(request, 'policyadmin/dashboard/settings.html', context)

@login_required
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
    return render(request, 'policyadmin/dashboard/enable_integration_form.html', context)


@login_required
@permission_required("constitution.can_add_integration", raise_exception=True)
def enable_integration(request, integration):
    """
    API Endpoint to enable a Metagov Plugin. This gets called on config form submission from JS.
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
    cp,created = cls.objects.get_or_create(
        community=community,
        team_id=plugin.community_platform_id,
        defaults={"community_name": plugin.community_platform_id}
    )
    logger.debug(f"CommunityPlatform '{cp.platform} {cp}' {'created' if created else 'already exists'}")

    return HttpResponse()


@login_required
@permission_required("constitution.can_remove_integration", raise_exception=True)
def disable_integration(request, integration):
    """
    API Endpoint to disable a Metagov plugin (navigated to from Settings page).
    This is the default implementation; platforms with PolicyKit integrations may override it.
    """
    id = int(request.GET.get("id")) # id of the plugin
    user = get_user(request)
    community = user.community.community
    logger.debug(f"Deleting plugin {integration} {id} for community {community}")

    # Delete the Metagov Plugin
    metagov.get_community(community.metagov_slug).disable_plugin(integration, id=id)

    # Delete the PlatformCommunity
    community_platform = community.get_platform_community(name=integration)
    if community_platform:
        community_platform.delete()

    return redirect("/main/settings")

@login_required
def editor(request):
    kind = request.GET.get('type', "platform").lower()
    operation = request.GET.get('operation', "Add")
    policy_id = request.GET.get('policy')

    user = get_user(request)
    community = user.community.community

    from policyengine.models import Policy, PolicyActionKind
    if kind not in [PolicyActionKind.PLATFORM, PolicyActionKind.CONSTITUTION, PolicyActionKind.TRIGGER]:
        raise Http404("Policy does not exist")

    policy = None
    if policy_id:
        try:
            policy = Policy.objects.get(id=policy_id, community=community)
        except Policy.DoesNotExist:
            raise Http404("Policy does not exist")

    if not policy or not policy.policy_template:
        # which action types to show in the dropdown
        actions = Utils.get_action_types(community, kinds=[kind])

        # list of autocomplete strings
        action_types = [a.codename for a in policy.action_types.all()] if policy else None
        autocompletes = Utils.get_autocompletes(community, action_types=action_types, policy=policy)

        base = DASHBOARD_BASE 

        if request.META.get('HTTP_HX_REQUEST'):
            base = DASHBOARD_BASE_AJAX

        data = {
            'user': get_user(request),
            'type': kind.capitalize(),
            'operation': operation,
            'actions': actions.items(),
            'autocompletes': json.dumps(autocompletes),
            'base': base
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
            data['variables'] = policy.variables.all()

        return render(request, 'policyadmin/dashboard/editor.html', data)
    else:
        import policyengine.frontend_utils as FrontendUtils
        user = get_user(request)
        nocode_modules = FrontendUtils.get_nocode_modules(user)
        nocode_modules['trigger'] = kind == PolicyActionKind.TRIGGER
        nocode_modules['policytemplate'] = json.dumps(policy.policy_template.to_nocode_json())
        return render(request, "no-code/main.html", nocode_modules)


@login_required
def selectrole(request):

    user = get_user(request)
    operation = request.GET.get('operation')

    roles = user.community.community.get_roles()

    return render(request, 'policyadmin/dashboard/role_select.html', {
        'user': user,
        'roles': roles,
        'operation': operation
    })

@login_required
def roleusers(request):
    from policyengine.models import CommunityUser

    user = get_user(request)
    operation = request.GET.get('operation')

    community = user.community.community
    roles = community.get_roles()
    users = {}
    for cp in community.get_platform_communities():
        users[cp.platform] = CommunityUser.objects.filter(community=cp).order_by('readable_name', 'username')

    return render(request, 'policyadmin/dashboard/role_users.html', {
        'roles': roles,
        'users': users.items(),
        'operation': operation
    })

@login_required
def roleeditor(request):
    from policyengine.models import CommunityPlatform, CommunityRole

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

@login_required
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

@login_required
def selectdocument(request):
    user = get_user(request)
    operation = request.GET.get('operation')

    show_active_documents = True
    if operation == 'Recover':
        show_active_documents = False

    documents = user.community.community.get_documents(is_active=show_active_documents)

    return render(request, 'policyadmin/dashboard/document_select.html', {
        'user': get_user(request),
        'documents': documents,
        'operation': operation
    })

@login_required
def documenteditor(request):
    from policyengine.models import CommunityDoc

    user = get_user(request)
    operation = request.GET.get('operation')
    doc_id = request.GET.get('doc')
    base = DASHBOARD_BASE 

    if request.META.get('HTTP_HX_REQUEST'):
        base = DASHBOARD_BASE_AJAX
        
    data = {
        'user': user,
        'operation': operation,
        'base': base
    }

    if doc_id:
        try:
            doc = CommunityDoc.objects.get(id=doc_id, community=user.community.community)
        except CommunityDoc.DoesNotExist:
            raise Http404("Document does not exist")

        data['name'] = doc.name
        data['text'] = doc.text

    return render(request, 'policyadmin/dashboard/document_editor.html', data)

@login_required
def actions(request):
    user = get_user(request)
    community = user.community.community

    from policyengine.models import PolicyActionKind
    actions = Utils.get_action_types(community, kinds=[PolicyActionKind.PLATFORM])
    return render(request, 'policyadmin/dashboard/actions.html', {
        'user': get_user(request),
        'actions': actions.items()
    })

@login_required
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

@login_required
def get_autocompletes(request):
    user = request.user
    community = user.community.community
    action_types = request.GET.get("action_types").split(",")
    if not action_types or len(action_types) == 1 and not action_types[0]:
        action_types = None
    autocompletes = Utils.get_autocompletes(community, action_types=action_types)
    return JsonResponse({'autocompletes': autocompletes})

@login_required
def error_check(request):
    """
    Takes a request object containing Python code data. Calls _lint_check(code)
    to check provided Python code for errors.
    Returns a JSON response containing the output and errors from linting.
    """
    data = json.loads(request.body)
    code = data['code']
    function_name = data['function_name']
    errors = _lint_check(code, function_name)
    return JsonResponse({'errors': errors})

@login_required
def policynew(request): 
    base = DASHBOARD_BASE 

    if request.META.get('HTTP_HX_REQUEST'):
        base = DASHBOARD_BASE_AJAX
        
    data = {
        'base': base
    }

    return render(request, 'policyadmin/dashboard/policy_new.html', data)

@login_required
def policy_action_save(request):
    from constitution.models import (ActionType, PolicyActionKind,
                                     PolicykitAddConstitutionPolicy,
                                     PolicykitAddPlatformPolicy,
                                     PolicykitAddTriggerPolicy,
                                     PolicykitChangeConstitutionPolicy,
                                     PolicykitChangePlatformPolicy,
                                     PolicykitChangeTriggerPolicy)

    from policyengine.models import Policy

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

        community = user.community.community

        try:
            action.policy = Policy.objects.get(pk=data['policy'], community=community)
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

    if "variables" in data:
        action.variables = data["variables"]

        try:
            action.parse_policy_variables(validate=True, save=False)
        except Exception as e:
            return HttpResponseBadRequest(e)

    try:
        action.save(evaluate_action=True)
    except Exception as e:
        logger.error(f"Error evaluating policy: {e}")
        return HttpResponseServerError()

    return HttpResponse()

@login_required
def policy_action_remove(request):
    from constitution.models import (PolicykitRemoveConstitutionPolicy,
                                     PolicykitRemovePlatformPolicy,
                                     PolicykitRemoveTriggerPolicy)

    from policyengine.models import Policy

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

@login_required
def policy_action_recover(request):
    from constitution.models import (PolicykitRecoverConstitutionPolicy,
                                     PolicykitRecoverPlatformPolicy,
                                     PolicykitRecoverTriggerPolicy)

    from policyengine.models import Policy

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

@login_required
def role_action_save(request):
    from constitution.models import PolicykitAddRole, PolicykitEditRole

    from policyengine.models import CommunityRole

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

@login_required
def role_action_users(request):
    from constitution.models import (PolicykitAddUserRole,
                                     PolicykitRemoveUserRole)

    from policyengine.models import CommunityRole, CommunityUser

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

@login_required
def role_action_remove(request):
    from constitution.models import PolicykitDeleteRole

    from policyengine.models import CommunityRole

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

@login_required
def document_action_save(request):
    from constitution.models import (PolicykitAddCommunityDoc,
                                     PolicykitChangeCommunityDoc)

    from policyengine.models import CommunityDoc

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

@login_required
def document_action_remove(request):
    from constitution.models import PolicykitDeleteCommunityDoc

    from policyengine.models import CommunityDoc

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

@login_required
def document_action_recover(request):
    from constitution.models import PolicykitRecoverCommunityDoc

    from policyengine.models import CommunityDoc

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

def policy_from_request (request, key_name = 'policy'):
    policy_id = request.GET.get(key_name)

    from policyengine.models import Policy

    # Get source policy object
    try:
        return Policy.objects.get(pk=policy_id)
    except Policy.DoesNotExist:
        raise Http404("Policy does not exist")

def embed_initial(request):
    # Get source policy based on id passed via the URL
    policy_source = policy_from_request(request, key_name="source")

    # Variables without a default value or value are set in the first step of the flow
    initial_variables = policy_source.variables.filter(default_value__exact="", value__exact="")

    # Variables are ordered with initial variables first
    all_variables = policy_source.variables.order_by("default_value")

    return render(request, "embed/initial.html", {
        "policy": policy_source,
        "initial_variables": initial_variables,
        "all_variables": all_variables
    })

def embed_setup (request):
    # TODO onboarding flow: starterkit, community, user, etc

    # TODO revert this
    from integrations.slack.models import SlackUser
    user = SlackUser.objects.last()
    community = user.community.community

    # Make a copy of the policy
    data = json.loads(request.body)
    policy_source = policy_from_request(request)
    new_policy = policy_source.copy_to_community(community=community, variable_data=data["variables"])

    return JsonResponse({ "policy": new_policy.id })

def embed_summary (request):
    policy = policy_from_request(request)

    variables = policy.variables.all()

    return render(request, "embed/summary.html", {
        "policy": policy,
        "all_variables": variables
    })

def embed_update (request):
    policy = policy_from_request(request)

    # Update policy variables
    data = json.loads(request.body)
    policy.update_variables(data["variables"])

    return JsonResponse({ "policy": policy.id })

def embed_edit (request):
    policy = policy_from_request(request)

    variables = policy.variables.all()

    return render(request, "embed/edit.html", {
        "policy": policy,
        "all_variables": variables
    })

def embed_success (request):
    policy = policy_from_request(request)

    return render(request, "embed/success.html", {
        "policy": policy
    })

@login_required
def main(request):
    import policyengine.frontend_utils as FrontendUtils
    reload = request.GET.get("reload", "false")
    if reload == "true":
        Utils.load_templates("Procedure")
        Utils.load_templates("Transformer")
        Utils.load_templates("FilterModule")

    user = get_user(request)
    nocode_modules = FrontendUtils.get_nocode_modules(user)
    nocode_modules['trigger'] = request.GET.get("trigger", "false")
    nocode_modules['policytemplate'] = json.dumps({})
    return render(request, "no-code/main.html", nocode_modules)

def view_policy_json(request):
    policy_id = request.GET.get("id")
    from policyengine.models import PolicyTemplate
    policy = PolicyTemplate.objects.get(pk=policy_id)
    policy_json = policy.to_json()
    return render(request, "no-code/view.html", {"policy_json": json.dumps(policy_json)})

def generate_code(request):
    body = json.loads(request.body)
    stage = body.get("stage", None)
    data = body.get("data", None)
    import policyengine.generate_codes as CodesGenerator
    codes = ""
    if(stage == "action"):
        custom_action_json = create_custom_action(data)
        codes = CodesGenerator.generate_filter_codes(custom_action_json)
    elif(stage == "execution_success"):
        codes = CodesGenerator.generate_execution_codes(data)
    elif(stage == "execution_fail"):
        codes = CodesGenerator.generate_execution_codes(data)
    
    try:
        # black's format_str() raises an exception if there's a syntax error
        codes = black.format_str(codes, mode=black.FileMode())
    except Exception as e:
        logger.error('Error when formatting code ', e)
    return JsonResponse({"status": True, "code": codes})

@login_required
def create_policy(request):
    data = json.loads(request.body)
    from policyengine.models import PolicyTemplate
    old_policytemplate = PolicyTemplate.objects.filter(pk=data.get("policytemplate")).first()
    if old_policytemplate and old_policytemplate.policy:
        policy = old_policytemplate.policy
    else:
        policy = None
    new_policytemplate = PolicyTemplate.objects.create(
        template_kind=data.get("policykind"),
        name=data.get("name", ""),
        description=data.get("description", "")
    )

    custom_actions_JSON = create_custom_action(data.get("filters", {}))
    new_policytemplate.add_custom_actions(custom_actions_JSON)

    create_procedure(data.get("procedure", {}), new_policytemplate)
    create_transformers(data.get("transformers", {}), new_policytemplate)
    create_execution(data.get("executions", {}), new_policytemplate)

    user = get_user(request)
    new_policy = new_policytemplate.create_policy(user.community.community, policy)
    return JsonResponse({"policytemplate": new_policytemplate.pk , "policy": new_policy.pk, "status": "success"})

def create_custom_action(filters):
    '''
        convert the frontend data to the custom actions JSON object;
        speciallly, replace all filter_pk with more details about each filter module

        parameters:
            filters: A Json object in the shape of
                [
                    {
                        "action_type": "slackpostmessage",
                        "filter": {
                            "message": {
                                "filter_pk": 1,
                                "platform": "slack",
                                "variables": {"word": "vote"}
                            },
                            "initiator": ...
                        }
                    },
                    ...
                ]
    '''

    from policyengine.models import FilterModule
    custom_action_JSON = []
    for filter in filters:
        action_type = filter.get("action_type")
        action_specs = filter.get("filter")
        '''
            check whether the value of each action_specs is an empty string
            an example of a action_specs:
                {
                    "initiator":{"filter_pk":"72", "platform": "slack", "variables":{"role":"test"}},
                    "text":{}
                }
        '''
        empty_filter = not any(["filter_pk" in value for value in list(action_specs.values()) ])
        filter_JSON = {}
        filter_JSON["action_type"] = action_type

        if not empty_filter:
            filter_JSON["action_type"] = action_type
            filter_JSON["filter"] = {}
            for field, filter_info in action_specs.items():
                if filter_info:
                    filter_module = FilterModule.objects.filter(pk=int(filter_info["filter_pk"])).first()
                    # create a filter JSON object with the actual value specified for each variable
                    filter_JSON["filter"][field] = filter_module.to_json(filter_info["variables"])
                    # to faciliate the generation of codes for custom actions, we store the platform of each filter
                    filter_JSON["filter"][field]["platform"] = filter_info["platform"]
        custom_action_JSON.append(filter_JSON)
    return custom_action_JSON

def create_procedure(procedure_data, policytemplate):
    '''
        Create the procedure field of a PolicyTemplate instance based on the procedure.
        We also add variables defined in the selected procedure to the new policytemplate instance

        Parameters:
            procedure:
                A Json object in the shape of
                {
                    "procedure_index": an integer, which represents the primary key of the selected procedure;
                    "procedure_variables": a dict of variable names and their values
                }
    '''
    from policyengine.models import Procedure
    if procedure_data:
        procedure_index = procedure_data.get("procedure_index", None)
        procedure = Procedure.objects.filter(pk=int(procedure_index)).first()
        if procedure:
            policytemplate.procedure = procedure
            policytemplate.add_variables(procedure.loads("variables"), procedure_data.get("procedure_variables", {}))
            policytemplate.add_descriptive_data(procedure.loads("data"))
            policytemplate.save()
    else:
        policytemplate.procedure = None
        policytemplate.save()

def create_transformers(transformer_data, policytemplate):
    """
        Add extra check modules and extra actions to the policy template
        parameters:
            transformer_data: e.g.,
                [

                    {
                        "module_index": 1,
                        "module_data": {
                            "duration": ...
                        }
                    }
                ]
    """
    from policyengine.models import Transformer

    for transformer in transformer_data or []:
        module_index = transformer.get("module_index", None)
        module_template = Transformer.objects.filter(pk=module_index).first()
        if module_template:
            policytemplate.add_transformer(module_template)
            policytemplate.add_variables(module_template.loads("variables"), transformer.get("module_data", {}))
            policytemplate.add_descriptive_data(module_template.loads("data"))
    policytemplate.save()

def create_execution(execution_data, policytemplate):
    """
        Add executions to success, fail, or notify blocks of the policytemplate instance

        parameters:
            "execution_data":
                {
                    "success": [
                        {
                            "action": "slackpostmessage",
                            "channel": ...,
                            "text": ...
                        }
                    ],
                    "fail": [{...}]
                }
    """
    for stage, executions in execution_data.items():
        policytemplate.add_executions(stage, executions)
