import black 
import json
import logging
import os

from django.apps import apps
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


logger = logging.getLogger(__name__)

INTEGRATION_ADMIN_ROLE_NAME = "Integration Admin"

# These functions get automatically passed "proposal" as the first argument,
# without the policy author needing to pass it manually.
SHIMMED_PROPOSAL_FUNCTIONS = ["initiate_vote", "post_message", "initiate_advanced_vote"]

def default_election_vote_message(policy):
    return "This action is governed by the following policy: " + policy.name + ". Decide between options below:\n"


def default_boolean_vote_message(policy):
    return f"This action is governed by the following policy: {policy.name}"


def get_or_create_integration_admin_role(community):
    from constitution.models import PolicykitAddIntegration, PolicykitRemoveIntegration
    from policyengine.models import CommunityRole

    role, created = CommunityRole.objects.get_or_create(community=community, role_name=INTEGRATION_ADMIN_ROLE_NAME)
    if created:
        content_type_1 = ContentType.objects.get_for_model(PolicykitAddIntegration)
        content_type_2 = ContentType.objects.get_for_model(PolicykitRemoveIntegration)
        permissions = Permission.objects.filter(content_type__in=[content_type_1, content_type_2])
        role.permissions.set(permissions)
    return role


def find_action_cls(codename: str, app_name=None):
    """
    Get the BaseAction subclass that has the specified codename
    """
    from policyengine.models import BaseAction

    if app_name:
        all_models = list(apps.get_app_config(app_name).get_models())
    else:
        listoflists = [
            list(a.get_models())
            for a in list(apps.get_app_configs())
            if "constitution" in a.name or "integration" in a.name
        ]
        all_models = [item for sublist in listoflists for item in sublist]

    for cls in all_models:
        if issubclass(cls, BaseAction) and cls._meta.model_name == codename:
            return cls
    return None


def get_action_classes(app_name: str):
    """
    Get a list of GovernableAction subclasses defined in the given app
    """
    from policyengine.models import GovernableAction

    actions = []
    for cls in apps.get_app_config(app_name).get_models():
        if issubclass(cls, GovernableAction):
            actions.append(cls)
    return actions


def get_trigger_classes(app_name: str):
    """
    Get a list of TriggerAction subclasses defined in the given app
    """
    from policyengine.models import TriggerAction

    actions = []
    for cls in apps.get_app_config(app_name).get_models():
        if issubclass(cls, TriggerAction):
            actions.append(cls)
    return actions


def get_action_types(community, kinds):
    from policyengine.models import PolicyActionKind, WebhookTriggerAction

    platform_communities = list(community.get_platform_communities())
    if PolicyActionKind.CONSTITUTION in kinds:
        platform_communities.append(community.constitution_community)
    actions = {}

    for c in platform_communities:
        app_name = c.platform
        action_list = []
        if (
            PolicyActionKind.PLATFORM in kinds
            or PolicyActionKind.TRIGGER in kinds  # all platformactions can be used as triggers
            or (PolicyActionKind.CONSTITUTION in kinds and app_name == "constitution")
        ):
            for cls in get_action_classes(app_name):
                action_list.append((cls._meta.model_name, cls._meta.verbose_name.title()))

        if PolicyActionKind.TRIGGER in kinds:
            for cls in get_trigger_classes(app_name):
                action_list.append((cls._meta.model_name, cls._meta.verbose_name.title()))
        if action_list:
            actions[app_name] = action_list

    # Special case to add generic trigger action
    if PolicyActionKind.TRIGGER in kinds:
        cls = WebhookTriggerAction
        action_list = [(cls._meta.model_name, cls._meta.verbose_name.title())]
        actions["any platform"] = action_list
    return actions


def get_autocompletes(community, action_types=None, policy=None):
    import policyengine.autocomplete as PkAutocomplete

    platform_communities = list(community.get_platform_communities())
    platform_communities_keys = [p.platform for p in platform_communities]

    # Add general autocompletes (proposal, policy, logger, and common fields on action)
    autocompletes = PkAutocomplete.general_autocompletes.copy()

    # Add autocompletes for policy's variable
    if policy:
        for variable in policy.variables.all() or []:
            variable_hint = PkAutocomplete.generate_variable_autocompletes(variable)
            autocompletes.extend(variable_hint)

    # Add autocompletes for each platform that this community is connected to
    for k, v in PkAutocomplete.integration_autocompletes.items():
        if k in platform_communities_keys:
            autocompletes.extend(v)
            autocompletes.append(k)

    # Add autocompletes for the selected action(s)
    for codename in action_types or []:
        cls = find_action_cls(codename)
        if cls:
            hints = PkAutocomplete.generate_action_autocompletes(cls)
            autocompletes.extend(hints)

    # remove duplicates (for example 'action.channel' would be repeated if SlackPostMessage and SlackRenameChannel selected)
    autocompletes = list(set(autocompletes))
    autocompletes.sort()
    return autocompletes


def get_platform_integrations():
    platform_integrations = []
    for a in apps.get_app_configs():
        if a.name.startswith("integrations"):
            platform_integrations.append(a.label)
    return platform_integrations


def get_action_content_types(app_name: str):
    from django.contrib.contenttypes.models import ContentType

    return [ContentType.objects.get_for_model(cls) for cls in get_action_classes(app_name)]

def render_starterkit_view(request, community_id, creator_username):
    from django.shortcuts import render
    request.session["starterkit_init_community_id"] = community_id
    request.session["starterkit_init_creator_username"] = creator_username

    context = {"starterkits": get_starterkits_info()}
    return render(request, "policyadmin/init_starterkit.html", context)

def get_starterkits_info():
    """
    Get a list of all starter-kit names and descriptions.
    """
    starterkits = []
    cur_path = os.path.abspath(os.path.dirname(__file__))
    dir_path = os.path.join(cur_path, "../starterkits")
    for kit_file in sorted(os.listdir(dir_path)):
        kit_path = os.path.join(dir_path, kit_file)
        f = open(kit_path)
        data = json.loads(f.read())
        if data.get("disabled"):
            continue
        starterkits.append({
            "id": kit_file.replace(".json", ""),
            "name": data["name"],
            "description": data["description"]
        })
    return starterkits


def get_all_permissions(app_names):
    content_types = []
    for c in app_names:
        content_types.extend(get_action_content_types(c))

    from django.contrib.auth.models import Permission
    from django.db.models import Q

    return Permission.objects.filter(content_type__in=content_types).filter(
        Q(name__startswith="Can add") | Q(name__startswith="Can execute")
    )


def _fill_templated_policy(policy_data, platform):
    return {k: v.replace("${PLATFORM}", platform) for k,v in policy_data.items()}

def initialize_starterkit_inner(community, kit_data, creator_username=None):
    from django.contrib.auth.models import Permission

    from policyengine.models import CommunityRole, CommunityUser, Policy

    # Some policies have templated ${PLATFORM} that need to be filled in with the platform string (eg "slack")
    initial_platform = community.get_platform_communities()[0].platform

    # Create platform policies
    for templated_policy in kit_data["platform_policies"]:
        policy = _fill_templated_policy(templated_policy, initial_platform)
        Policy.objects.create(**policy, kind=Policy.PLATFORM, community=community)

    # Create constitution policies
    for templated_policy in kit_data["constitution_policies"]:
        policy = _fill_templated_policy(templated_policy, initial_platform)
        Policy.objects.create(**policy, kind=Policy.CONSTITUTION, community=community)

    # Create roles
    for role in kit_data["roles"]:
        r, _ = CommunityRole.objects.update_or_create(
            is_base_role=role["is_base_role"],
            community=community,
            defaults={"role_name": role["name"], "description": role["description"]},
        )

        # Add PolicyKit-specific permissions
        r.permissions.set(Permission.objects.filter(name__in=role["permissions"]))

        # Add constitution permissions
        constitution_content_types = get_action_content_types("constitution")
        _add_permissions_to_role(r, role["constitution_permission_sets"], constitution_content_types)

        # Add permissions for each platform GovernableAction (for all platforms, not just the enabled one)
        action_content_types = []
        for platform in get_platform_integrations():
            content_types = get_action_content_types(platform)
            action_content_types.extend(content_types)
        _add_permissions_to_role(r, role["platform_permission_sets"], action_content_types)

        if role["user_group"] == "all":
            group = CommunityUser.objects.filter(community__community=community)
        elif role["user_group"] == "admins":
            group = CommunityUser.objects.filter(community__community=community, is_community_admin=True)
        elif role["user_group"] == "nonadmins":
            group = CommunityUser.objects.filter(community__community=community, is_community_admin=False)
        elif role["user_group"] == "creator":
            if not creator_username:
                raise Exception(f"can't initialize kit {kit_data['name']} without the username of the creator")
            group = CommunityUser.objects.filter(username=creator_username)

        # logger.debug(f"Adding {group.count()} users to role {r.role_name}")
        for user in group:
            r.user_set.add(user)

        r.save()

def _add_permissions_to_role(role, permission_sets, content_types):
    from django.contrib.auth.models import Permission

    if "view" in permission_sets:
        view_perms = Permission.objects.filter(content_type__in=content_types, name__startswith="Can view")
        role.permissions.add(*view_perms)
    if "propose" in permission_sets:
        propose_perms = Permission.objects.filter(content_type__in=content_types, name__startswith="Can add")
        role.permissions.add(*propose_perms)
    if "execute" in permission_sets:
        execute_perms = Permission.objects.filter(content_type__in=content_types, name__startswith="Can execute")
        role.permissions.add(*execute_perms)

def determine_action_app(codename):
    """ get the corresponding app name: constitution, slack, etc."""
    action_class = find_action_cls(codename)
    return action_class._meta.app_label

def determine_action_kind(codename):
    """ get the corresponding action kind: PLATFORM, CONSTITUTION"""
    from policyengine.models import Policy
    action_class = find_action_cls(codename)
    app_label = action_class._meta.app_label
    if app_label == "constitution":
        return Policy.CONSTITUTION
    else:
        return Policy.PLATFORM

def determine_policy_kind(is_trigger, app_name):
    from policyengine.models import Policy
    if is_trigger:
        return Policy.TRIGGER
    elif app_name == "constitution":
        return Policy.CONSTITUTION
    else:
        return Policy.PLATFORM

def dump_to_JSON(object, json_fields):
    for field in json_fields:
        object[field] = json.dumps(object[field])
    return object

def load_templates(kind):
        """
            Load procedute and module templates for a given platform
        """

        cur_path = os.path.abspath(os.path.dirname(__file__))
        logger.debug(f"Loading {kind} templates from {cur_path}")
        if kind == "Procedure":
            from policyengine.models import Procedure
            Procedure.objects.all().delete()
            procedure_path = os.path.join(cur_path, "../policytemplates/procedures.json")
            with open(procedure_path) as f:
                procedure_data = json.loads(f.read())
                for procedure in procedure_data:
                    procedure = dump_to_JSON(procedure, Procedure.JSON_FIELDS)
                    Procedure.objects.create(**procedure)
        elif kind == "Transformer":
            from policyengine.models import Transformer
            Transformer.objects.all().delete()
            checkmodule_path = os.path.join(cur_path, "../policytemplates/modules.json")
            with open(checkmodule_path) as f:
                checkmodule_data = json.loads(f.read())
                for checkmodule in checkmodule_data:
                    checkmodule = dump_to_JSON(checkmodule, Transformer.JSON_FIELDS)
                    Transformer.objects.create(**checkmodule)
        elif kind == "FilterModule":
            from policyengine.models import FilterModule
            FilterModule.objects.all().delete()
            filtermodule_path = os.path.join(cur_path, "../policytemplates/filters.json")
            with open(filtermodule_path) as f:
                filtermodule_data = json.loads(f.read())
                for filtermodule in filtermodule_data:
                    filtermodule = dump_to_JSON(filtermodule, FilterModule.JSON_FIELDS)
                    FilterModule.objects.create(**filtermodule)

def load_entities(platform, get_slack_users=False):
    SUPPORTED_ENTITIES = [
        "CommunityUser", "Role", "Permission", "SlackChannel", "Expense", "SlackUser"
    ]

    entities = {}
    # extract all readable names of CommunityUsers on this platform
    entities["CommunityUser"] = [{"name": user.readable_name, "value": user.username} for user in platform.get_users()]

    # extract all roles on this platform
    entities["Role"] = [{"name": role.role_name, "value": role.role_name } for role in platform.get_roles()]

    # extract all permissions on this platform
    entities["Permission"] = [{"name": permission.name, "value": permission.codename } for permission in get_all_permissions([platform.platform])]

    entities["Expense"] = [{"name": "Invoice", "value": "INVOICE"}, {"name": "Reimbursement", "value": "REIMBURSEMENT"}]

    # entities["Expense"] = [
    #     {"name": "Invoice", "value": "Invoice"}, {"name": "Reimbursement", "value": "Reimbursement"}
    # ]

    # extract all Slack channels in this platform
    if platform.platform.upper() == "SLACK":
        entities["SlackChannel"] = [
                            {
                                "name": channel.get("name", channel["id"]),
                                "value": channel["id"]
                            } for channel in platform.get_conversations(types=["channel"], types_arg="private_channel")
                        ]
    if get_slack_users:
        entities["SlackUser"] = platform.get_real_users()
    return entities

def get_filter_parameters(app_name, action_codename):
    """
        Get the designated filter parameters for a GovernableAction
    """
    action_model = apps.get_model(app_name, action_codename)
    if hasattr(action_model, "FILTER_PARAMETERS"):
        return action_model.FILTER_PARAMETERS
    else:
        return []

def check_code_variables(string):
    """
        Check whether the string contains any embedded variables or data, and format it accordingly
        TODO: check whether the referenced variables or data are defined
    """
    import re
    pattern = r'\{.*?\}'
    return re.search(pattern, string) is not None

def validate_fstrings(string):
    import re
    pattern = r'{\s*}'
    # Regular expression pattern to match empty curly brackets
    return re.sub(pattern, '', string)

def determine_user(platform, username):
    from policyengine.models import CommunityUser
    if CommunityUser.objects.filter(username=username, community=platform).exists():
        return CommunityUser.objects.get(username=username, community=platform)
    elif CommunityUser.objects.filter(readable_name=username, community=platform).exists():
        return CommunityUser.objects.get(readable_name=username, community=platform)
    else:
        return None

def sanitize_code(codes):
    """ 
        Sanitize the code by escaping special characters
        In the js frontend, \n will be interpreted as a new line, 
        so we replace it with \\n, which will be parsed as \n
        Similarly for \t.
        We wrap the entire json string with the backticks; 
        given that backticks are rarely used in python code, we simply remove them.
        For double quotes, if there are just at the one nested level (i.e., \"), we will escape them with \\".
        This will be parsed as \n in the js frontend.
        But if double quotes are nested within two layers (i.e., \\\\\"), the first replace function will escape them to six backslashes,
        so we further replace them to make them seven backslashes, which will be parsed as \\\" in the js frontend.
    """
    return codes.replace("\n", "\\n").replace("\t", "\\t").replace('\"', '\\"').replace('\\\\\"', '\\\\\\"').replace('`', '')

def format_code(codes):
    try:
        # black's format_str() raises an exception if there's a syntax error
        codes = black.format_str(codes, mode=black.FileMode())
        return codes
    except Exception as e:
        logger.error('Error when formatting code ', e)
        return None

def translate_policy_to_template_format(policy):
    """
    Translate a policy into the format used by policy templates.
    """
    def escape_single_quotes(codes):
        return codes.replace("\n", "\\n").replace("\t", "\\t")

    from policyengine.models import PolicyTemplate, Policy, CustomAction, Procedure
    if policy.kind in [Policy.PLATFORM, Policy.CONSTITUTION]:
        template_kind = PolicyTemplate.COMMUNITY_POLICIES
    else:
        template_kind = PolicyTemplate.TRIGGERING_POLICIES
    
    new_template = PolicyTemplate(
        name=policy.name,
        description=policy.description,
        template_kind=template_kind,
    )
    new_template.save()

    """Custom Action translation"""
    # since the filter is written in codes, we will treat it as a custom action
    # create an empty custom action first
    custom_action = CustomAction()
    custom_action.save()
    logger.debug(policy.filter)
    logger.debug(policy.check)
    logger.debug(policy.initialize)
    logger.debug(policy.notify)
    logger.debug(policy.success)
    logger.debug(policy.fail)
    custom_action.action_types.add(*policy.action_types.all())
    # we treat the filter as the codes at the codes view
    custom_action.dumps("filter", {
        "view": "codes",
        "codes": policy.filter
    })
    custom_action.save()
    
    new_template.custom_actions.add(custom_action)

    """Procedure translation"""
    custom_procedure = Procedure(
        name=policy.name,
        description=policy.description,
        is_template=False,
        view="codes",
    )
    custom_procedure.dumps("initialize", escape_single_quotes(policy.initialize))
    custom_procedure.dumps("check", escape_single_quotes(policy.check))
    # if the notify is of the code view, then it is simply a string of codes;
    # only if it is of the form view, then it is a list of executions.
    custom_procedure.dumps("notify", escape_single_quotes(policy.notify))
    custom_procedure.save()
    new_template.procedure = custom_procedure

    """Execution translation"""
    new_template.dumps("executions", {
        "success": [{
            "view": "codes",
            "codes": escape_single_quotes(policy.success)
        }],
        "fail": [{
            "view": "codes",
            "codes": escape_single_quotes(policy.fail)
        }]
    })
    new_template.save()
    
    return new_template
    