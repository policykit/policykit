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
SHIMMED_PROPOSAL_FUNCTIONS = ["initiate_vote", "post_message"]

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
    dir_path = os.path.join(cur_path, f"../starterkits")
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

def force_variable_types(value, variable):
    """
        when generating codes, we need to make sure the value specified by users (a string) are correctly embedded in the codes
        in accordance with the variable type (e.g., string, number, list of string, list of number) 
    """     
    value_codes = ""
    if value == "" or value is None:
        """
            For now we assume an empty string represents None in the execution codes 
            as we do not know whether an empty string is no input or actually an empty string
            
            We do not need to replace value with the default value of this variable here,
            as we load default values in the input box of the frontend, and if users make no change,
            the value will automatically be the default value.
        """
        value_codes = "None"
    else:
        if variable["is_list"]:
            if variable["type"] == "number" or variable["type"] == "float":
                # e.g., value = "1, 2, 3", then codes should be "[1, 2, 3]"
                value_codes = f"[{value}]"
            elif variable["type"] == "string":
                # e.g., value = "test1, test2, test3", then codes should be "[\"test1\", \"test2\", \"test3\"]"
                value_list = value.split(",")
                value_codes = "["
                for value in value_list:
                    value_codes += f"\"{value}\","
                value_codes = value_codes[:-1] # remove the last comma
                value_codes += "]"
            else:
                raise Exception(f"variable type {variable['type']} is not supported for list")
        else:
            if variable["type"] in ["number", "float", "timestamp"]:
                # e.g., value = "1", then codes should be "1" and we treat timestamp as an integer
                value_codes = f"{value}"
            elif variable["type"] == "string":
                # e.g., value = "test", then codes should be "\"test\""
                value_codes = f"\"{value}\""
            else:
                raise NotImplementedError
    return value_codes

def extract_action_types(filters):
    """ 
    extract all ActionTypes defined in a list of CustomActions JSON
    e.g.,
        [
            {
                "action_type": "slackpostmessage",
                "filter": {
                    "initiator": {
                        "kind": "CommunityUser",
                        "name": "Role",
                        "variables": [
                                {
                                    "name": "role",
                                    "type": "string",
                                    "value": "hello"
                                }
                            ]
                    },
                    "text": {
                        "kind": "Text",
                        "name": "Startswith",
                        "variables": [
                            {
                                "name": "word",
                                "type": "string",
                                "value": "test"
                            }
                        ]
                    }
                },
                "community_name": null
            },
            {
                "action_type": "slackrenameconversation"
            }
        ],
    """
    from policyengine.models import ActionType
    action_types = []
    for filter in filters:
        action_codename = filter["action_type"]
        action_type = ActionType.objects.filter(codename=action_codename).first()
        if action_type:
            action_types.append(action_type)
    return action_types


def generate_filter_codes(filters):
    """
        Generate codes from a list of filters defined in JSON
        See examples of the parameter filters above 

        The generated codes will be in the shape of 
        if action.action_type == "slackpostmessage":
	        def CommunityUser_Role(role, object=None):
		        all_usernames_with_roles = [_user.username for _user in slack.get_users(role_names=[role])]
		        return (object.username in all_usernames_with_roles) if object else None, all_usernames_with_roles
	        def Text_Equals(text, object=None):
		        return object == text, None
	        return CommunityUser_Role("test", action.initiator)[0] and Text_Equals("test", action.text)[0]

    """

    from policyengine.models import FilterModule

    filter_codes = ""
    for action_filter in filters:
        # we first check whether the action is the one we want to apply filters to
        filter_codes += "if action.action_type == \"{action_type}\":\n\t".format(action_type = action_filter["action_type"])
        # one example: "if action.action_type == \"slackpostmessage\":\n\t
        
        now_codes = []
        function_calls = [] # a list of names of filter functions we will call in the end for each action type
        
        # only custom actions have the filter key
        for field, field_filter in action_filter.get("filter", {}).items():
            """  e.g.,
                    "initiator": {
                        "kind": "CommunityUser",
                        "name": "Role",
                        "variables": [
                            {
                                "name": "role",
                                "label": "Which role users should have?",
                                "entity": "Role",
                                "default_value": null,
                                "is_required": true,
                                "prompt": "",
                                "type": "string",
                                "is_list": false
                            }
                        ],
                        "platform": "slack"
                    },
            """
            if field_filter:
                filter = FilterModule.objects.filter(kind=field_filter["kind"], name=field_filter["name"]).first()
                if not filter:
                    raise Exception(f"Filter {field_filter['kind']}_{field_filter['name']} not found")
                
                field_filter["codes"] = filter.codes
                parameters_codes = "object, " + ", ".join([var["name"]  for var in field_filter["variables"]])
                # in case the filter is used to filter out a list of entities
                now_codes.append(
                    "def {kind}_{name}({parameters}):".format(
                        kind = field_filter["kind"], 
                        name = field_filter["name"],
                        parameters = parameters_codes
                    )
                ) # result example: def CommunityUser_Role(role, object=None):


                module_codes = field_filter["codes"].format(platform=field_filter["platform"])
                # in case the exact platform such as slack is used in the codes
                module_codes = ["\t" + line for line in module_codes.splitlines()]
                # because these codes are put inside a function, we need to indent them

                now_codes.extend(module_codes)

                parameters_called = []
                parameters_called.append("action.{field}".format(field=field)) # action.initiator
                for var in field_filter["variables"]:
                    # we need to make sure the value specified by users (a string) are correctly embedded in the codes
                    parameters_called.append(force_variable_types(var["value"], var))
                parameters_called = ", ".join(parameters_called) # "test", action.initiator
                function_calls.append(
                    "{kind}_{name}({parameters})".format(
                        kind = field_filter["kind"], 
                        name = field_filter["name"], 
                        parameters = parameters_called
                    )
                )
        if now_codes:
            filter_codes += "\n\t".join(now_codes) + "\n\treturn " + " and ".join(function_calls) + "\n"
        else:
            filter_codes += "return True\n"
    return filter_codes

def generate_initialize_codes(data):
    """
        Help generate codes for calculating static data, as codes for dynamic data have already been included in check codes
    """
    initialize_codes = ""
    for datum in data:
        if(datum["dynamic"] == False):
            initialize_codes += datum["codes"] 
            # e.g. board_members = [user.username for user in slack.get_users(role_names=[variables[\"board_role\"]])]
            initialize_codes += "proposal.data.set(\"{name}\", {name})".format(name=datum["name"]) + "\n"
            # e.g. proposal.set("board_members", board_members)
    if not initialize_codes:
        initialize_codes = "pass"
    return initialize_codes

def generate_check_codes(checks):
    """
        a list of checks defined in JSON
        We assume the last check is the one representing the referenced procedure, 
        and we will use its name to find the procedure
        e.g. 
        [
            {
                "name": "Enforce procedure time restrictions",
                "description": "..."
            },
            {
                "name": "Consesus Voting",
                "description": "..."
            }
        ],
    """
    from policyengine.models import CheckModule, Procedure
    # in cases when the user writes a policy without any checks (e.g., a if-then rules)
    if(len(checks) == 0):
        return "pass"
    
    check_codes = ""
    for check in checks[:-1]:
        check_module = CheckModule.objects.filter(name=check["name"]).first()
        if not check_module:
            raise Exception(f"When generating check codes, CheckModule {check['name']} not found")
        check_codes += check_module.codes
    
    # the last check is the one representing the referenced procedure
    procedure = Procedure.objects.filter(name=checks[-1]["name"]).first()
    if not procedure:
        raise Exception(f"When generating check codes, Procedure {checks[-1]['name']} not found")
    procedure_check = procedure.loads("check")
    if "codes" not in procedure_check:
        raise Exception(f"When generating check codes, Procedure {checks[-1]['name']} does not have check codes")
    check_codes += procedure_check["codes"]

    return check_codes

def generate_initiate_votes(execution):
    codes = ""
    
    if execution["platform"] == "slack" and execution["action"] == "initiate_vote":
        if execution.get("post_type") == "\"mpim\"":
            execution["channel"] = "None"
        
        codes = "slack.initiate_vote(users={users}, text={text}, post_type={post_type}, channel={channel}, options={options})".format(
                    users = execution["users"],
                    text = execution["vote_message"],
                    post_type = execution["post_type"],
                    channel = execution["channel"],
                    options = None
                )
    elif execution["platform"] == "slack" and execution["action"] == "initiate_advanced_vote":
        codes = "slack.initiate_advanced_vote(candidates={candidates}, options={options}, users={users}, channel={channel}, title={title}, details={details})".format(
                    candidates = execution["candidates"],
                    options = execution["options"],
                    users = execution["users"],
                    channel = execution["channel"],
                    title=execution["title"],
                    details = execution["details"]
                )
    else:
        raise NotImplementedError
    return codes

def initiate_execution_variables(platform, vote_type):
    """
        Ideally, we should create a new BaseAction for initating votes in each integration, 
        and specify execution variables. But for now, we just hardcode them here, 
        since an addition of a new BaseAction may involve other more fundamental changes
    """
    if platform == "slack" and vote_type == "initiate_vote":
        return [
            {
                "name": "channel",
                "label": "Channel to post the vote",
                "entity": "SlackChannel",
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": False
            },
            {
                "name": "users",
                "label": "Eligible voters",
                "entity": "SlackUser",
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": True
            },
            {
                "name": "vote_message",
                "label": "Message to be posted when initiating the vote",
                "entity": None,
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": False
            },
            {
                "name": "post_type",
                "label": "How to post the vote in Slack",
                "entity": None,
                "default_value": "channel",
                "is_required": False,
                "prompt": "",
                "type": "string",
                "is_list": False
            }
        ]
    elif platform == "slack" and vote_type == "initiate_advanced_vote":
        return [
            {
                "name": "candidates",
                "label": "Candidates that users can vote for",
                "entity": None,
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": True
            },
            {
                "name": "options",
                "label": "Options that users can select for each candidate",
                "entity": None,
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": True
            },
            {
                "name": "users",
                "label": "Eligible voters",
                "entity": "SlackUser",
                "default_value": "",
                "is_required": False,
                "prompt": "",
                "type": "string",
                "is_list": True
            },
            {
                "name": "channel",
                "label": "Channel to post the vote",
                "entity": "SlackChannel",
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": False
            },
            {
                "name": "title",
                "label": "Message to be posted when initiating the vote",
                "entity": None,
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": False
            },
            {
                "name": "details",
                "label": "Message to be posted when initiating the vote",
                "entity": None,
                "default_value": "",
                "is_required": False,
                "prompt": "",
                "type": "string",
                "is_list": False
            }
        ]
    else:
        raise NotImplementedError

def force_execution_variable_types(execution, variables_details):
    """
        a wrapper function for force_variable_types when generating codes for an execution
    """

    for name, value in execution.items():
        if name in ["action", "platform"]:
            continue
        if value.startswith("variables"):
            # parts after the first dot is the name of the variable
            var_name = value.split(".", 1)[1]
            execution[name] = f"variables[\"{var_name}\"]"
        elif value.startswith("data"):
            # value e.g., data.board_members
            datum_name = value.split(".", 1)[1]
            execution[name] = f"proposal.data.get(\"{datum_name}\")"
        else:
            """ 
                if the value is not a PolicyVariable or data, we need to convert it to the expected type
                Otherwise, this is not needed because we explictly force all PolicyVariables 
                to be expected types in EvaluationContext before executing codes 
            """
            var_detail = [var for var in variables_details if var["name"] == name]
            if len(var_detail) > 0:
                execution[name] = force_variable_types(value, var_detail[0])

    return execution

def generate_execution_codes(executions):

    """ 
    Help generate codes for a list of executions. 
    
    some examples of executions:
        [
            {
                "action": "initiate_vote",
                "vote_message": "variables.vote_message",
                "vote_type": "boolean",
                "users": "variables.users",
                "channel": "variables.vote_channel",
                "platform": "slack"
            }
        ]
    or
        [
            {   
                "action": "slackpostmessage",
                "text": "LeijieWang",
                "channel": "test-channel",
                "frequency": "60"
            }
        ],
    """

    execution_codes = []
    for execution in executions:
        codes = ""
        if "frequency" in execution:
            # if the execution has a frequency, then it is a recurring execution
            # we need to add the frequency to the execution
            duration_variable = "last_time_" + execution["action"]
            codes += f"if not proposal.data.get(\"{duration_variable}\"):\n\tproposal.data.set(\"{duration_variable}\", proposal.get_time_elapsed().total_seconds())\nif proposal.vote_post_id and ((proposal.get_time_elapsed().total_seconds() - proposal.data.get(\"{duration_variable}\")) > int({execution['frequency']})) * 60:\n\tproposal.data.set(\"duration_variable\", proposal.get_time_elapsed().total_seconds())\n\t"

        if execution["action"] == "initiate_vote" or execution["action"] == "initiate_advanced_vote":
            execute_variables = initiate_execution_variables(execution["platform"], execution["action"])
            execution = force_execution_variable_types(execution, execute_variables)
            codes += generate_initiate_votes(execution)
        elif execution["action"] == "action.revert":
            codes += "action.revert()"
        elif execution["action"] == "action.execute":
            codes += "action.execute()"
        else:
            # currently only support slackpostmessage
            action_codename = execution["action"]
            this_action = find_action_cls(action_codename)
            if hasattr(this_action, "execution_codes"):
                execute_variables = this_action.EXECUTE_VARIABLES
                execution = force_execution_variable_types(execution, execute_variables)
                codes += this_action.execution_codes(**execution)
            else:
                raise NotImplementedError
        execution_codes.append(codes)
    return "\n".join(execution_codes) + "\n"

def get_filter_parameters(app_name, action_codename):
    """
        Get the designated filter parameters for a GovernableAction
    """
    action_model = apps.get_model(app_name, action_codename)
    if hasattr(action_model, "FILTER_PARAMETERS"):
        return action_model.FILTER_PARAMETERS
    else:
        return []
    
def determine_policy_kind(is_trigger, app_name):
    from policyengine.models import Policy
    if is_trigger:
        return Policy.TRIGGER
    elif app_name == "constitution":
        return Policy.CONSTITUTION
    else:
        return Policy.PLATFORM

def get_execution_variables(app_name, action_codename):
    action_model = apps.get_model(app_name, action_codename)
    if hasattr(action_model, "execution_codes"):
        return action_model.EXECUTE_VARIABLES
    else:
        return None
    
def extract_executable_actions(community):
    from policyengine.models import PolicyActionKind
    actions = get_action_types(community, kinds=[PolicyActionKind.PLATFORM, PolicyActionKind.CONSTITUTION])

    executable_actions = dict()
    execution_variables = dict()
    for app_name, action_list in actions.items():
        for action_code, action_name in action_list:
            variables = get_execution_variables(app_name, action_code)
            # only not None if the action has execution_codes function
            if variables:
                if app_name not in executable_actions:
                    executable_actions[app_name] = []
                executable_actions[app_name].append((action_code, action_name))
                execution_variables[action_code] = variables
    
    return executable_actions, execution_variables

def dump_to_JSON(object, json_fields):
    for field in json_fields:
        object[field] = json.dumps(object[field])
    return object

def load_templates(kind):
        """
            Load procedute and module templates for a given platform
        """
            
        cur_path = os.path.abspath(os.path.dirname(__file__))
        if kind == "Procedure":
            from policyengine.models import Procedure
            Procedure.objects.all().delete()
            procedure_path = os.path.join(cur_path, f"../policytemplates/procedures.json")
            with open(procedure_path) as f:
                procedure_data = json.loads(f.read())
                for procedure in procedure_data:
                    procedure = dump_to_JSON(procedure, Procedure.JSON_FIELDS)
                    Procedure.objects.create(**procedure)
        elif kind == "CheckModule":
            from policyengine.models import CheckModule
            CheckModule.objects.all().delete()
            checkmodule_path = os.path.join(cur_path, f"../policytemplates/modules.json")
            with open(checkmodule_path) as f:
                checkmodule_data = json.loads(f.read())
                for checkmodule in checkmodule_data:
                    checkmodule = dump_to_JSON(checkmodule, CheckModule.JSON_FIELDS)
                    CheckModule.objects.create(**checkmodule)
        elif kind == "FilterModule":
            from policyengine.models import FilterModule
            FilterModule.objects.all().delete()
            filtermodule_path = os.path.join(cur_path, f"../policytemplates/filters.json")
            with open(filtermodule_path) as f:
                filtermodule_data = json.loads(f.read())
                for filtermodule in filtermodule_data:
                    filtermodule = dump_to_JSON(filtermodule, FilterModule.JSON_FIELDS)
                    FilterModule.objects.create(**filtermodule)

def load_entities(platform):
    SUPPORTED_ENTITIES = ["CommunityUser", "Role", "Permission", "SlackChannel"]
    
    entities = {}
    # extract all readable names of CommunityUsers on this platform
    entities["CommunityUser"] = [{"name": user.readable_name, "value": user.username} for user in platform.get_users()]

    # extract all roles on this platform
    entities["Role"] = [{"name": role.role_name, "value": role.role_name } for role in platform.get_roles()]

    # extract all permissions on this platform
    entities["Permission"] = [{"name": permission.name, "value": permission.codename } for permission in get_all_permissions([platform.platform])]

    # extract all Slack channels in this platform
    if platform.platform.upper() == "SLACK":
        entities["SlackChannel"] = [
                            {
                                "name": channel.get("name", channel["id"]), 
                                "value": channel["id"]
                            } for channel in platform.get_conversations(types=["channel"])
                        ]
    return entities

