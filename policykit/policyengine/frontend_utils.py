import policyengine.utils as Utils
from django.apps import apps
import json, logging
logger = logging.getLogger(__name__)

def get_filter_parameters(app_name, action_codename):
    """
        Get the designated filter parameters for a GovernableAction
    """
    action_model = apps.get_model(app_name, action_codename)
    if hasattr(action_model, "FILTER_PARAMETERS"):
        return action_model.FILTER_PARAMETERS
    else:
        return []

def remove_platform_prefix(action_name, appname):
    """
        Remove the platform prefix from an action name
        For instance, Slack Post Message --> Post Message
    """
    if appname == "constitution":
        appname = "policykit" # as constitution actions start with the word "policykit" instead of "constitution"
    action_name = action_name.replace(appname, "").replace(appname.capitalize(), "")
    return action_name.strip()

def get_base_actions(user):
    """
        determine a list of actions users can use as a base action of a custom action, 
            and for each action, determine the filter kinds that can be applied to each action field 
        The resultant base_actions is a dictionary of app_name: [(action_code, action_name), ...]
        The resultant filter_kinds_for_fields is a dictionary of action_code: {field_name: filter_kind, ...}
    """
    from policyengine.models import PolicyActionKind

    filter_kinds_dict = {}
    base_actions = {}
    actions = Utils.get_action_types(user.community.community, kinds=[PolicyActionKind.PLATFORM, PolicyActionKind.CONSTITUTION])    
    for app_name, action_list in actions.items(): # iterate all Governable actions for each app
        base_action_list = []
        for action_code, verbose_name in action_list:
            parameter = get_filter_parameters(app_name, action_code)
            # only select actions that have filter parameters
            if parameter:
                filter_kinds_dict[action_code] = parameter
                base_action_list.append({
                    "value": action_code,
                    "name": get_action_name(app_name, action_code),
                    "app": app_name
                })
        # only show apps that have at least one action with filter parameters
        if base_action_list:
            base_actions[app_name] = base_action_list
    return base_actions, filter_kinds_dict

def get_filter_modules(apps):
    """
        For each app, get all filter modules available listed by kind (CommunityUser, Text, Channel, etc.)
        The resultant filters is a dictionary of app_name: {kind: [filter_module, ...], ...}
    """
    from policyengine.models import FilterModule
    filter_modules = {}
    for app_name in apps:
        filter_modules[app_name] = {}
        filters_per_app = FilterModule.objects.filter(platform__in=[app_name, "All"])
        # get all distinct filter kinds for each app
        filter_kinds = list(filters_per_app.values_list('kind', flat=True).distinct())
        for kind in filter_kinds: # iterate all filter kinds for each app
            filter_modules[app_name][kind] = []
            for filter in filters_per_app.filter(kind=kind):
                filter_modules[app_name][kind].append({
                    "pk": filter.pk, 
                    "name": filter.name,
                    "description": filter.description, 
                    "prompt": filter.prompt,
                    "variables": filter.loads("variables"),
                    "data": filter.loads("data"),
                    "app": app_name
                })
    return filter_modules

def get_all_platforms(user):
    # get all platforms this community is on
    platforms = user.community.community.get_platform_communities()
    platform_names = [platform.platform for platform in platforms]
    return platform_names



def get_procedures(platforms):
    from policyengine.models import Procedure
    # load all procedure templates
    procedure_objects= Procedure.objects.filter(is_template=True).all()
    procedures = { platform: [] for platform in platforms }
   
    for template in procedure_objects:
        procedures[template.platform.lower()].append({
            "name": template.name, 
            "description": template.description,
            "value": template.pk, 
            "variables": template.loads("variables"),
            "data": template.loads("data"),
            "app": template.platform.lower(),
            "codes": Utils.sanitize_code(template.loads("check"))
        })
    return procedures

def get_transformers():
    from policyengine.models import Transformer
    
    # prepare information about module templates
    transformers_objects = Transformer.objects.filter(is_template=True).all()
    transformers = []
    for template in transformers_objects:
        transformers.append({
            "name": template.name, 
            "value": template.name,  # we assume that the name is unique
            "description": template.description,
            "variables": template.loads("variables"),
            "app": "all",
            "codes": Utils.sanitize_code(template.codes)
        })
    return {"all": transformers}

def get_execution_variables(app_name, action_codename):
    action_model = apps.get_model(app_name, action_codename)
    if hasattr(action_model, "execution_codes"):
        return action_model.EXECUTE_VARIABLES
    else:
        return None
    
def get_action_name(app_name, action_codename):
    action_model = apps.get_model(app_name, action_codename)
    if hasattr(action_model, "ACTION_NAME"):
        return action_model.ACTION_NAME
    else:
        logger.error("ACTION_NAME not found for %s.%s" % (app_name, action_codename))
    
def get_nocode_modules(user):
    base_actions, action_filter_kinds = get_base_actions(user)
    # for filter modules, only show the ones that are applicable to platforms base actions are available on
    filter_modules = get_filter_modules(list(base_actions.keys()))

    # get all platforms this community is on
    platforms = get_all_platforms(user)
    # get all procedures available to this community
    procedures = get_procedures(platforms)

    # get all transformers available to this community
    transformers = get_transformers()

    # get all execution modules available to this community
    executions = extract_executable_actions(user)

    # get all entities in the community
    entities = load_entities(user.community)
    return {
        "base_actions": json.dumps(base_actions),
        "action_filter_kinds": json.dumps(action_filter_kinds),
        "filter_modules": json.dumps(filter_modules),
        "platforms": json.dumps(platforms),
        "procedures": json.dumps(procedures),
        "transformers": json.dumps(transformers),
        "executions": json.dumps(executions),
        "entities": json.dumps(entities),
    }

def extract_executable_actions(user):
    from policyengine.models import PolicyActionKind
    from policyengine.utils import get_action_types
    actions = get_action_types(user.community.community, kinds=[PolicyActionKind.PLATFORM, PolicyActionKind.CONSTITUTION])

    executable_actions = dict()
    executable_actions[" "] = [{
        "value": "revert_action",
        "name": "Revert the Trigger Actions",
        "variables": [],
        "app": " "
    }]

    executable_actions[" "].append({
        "value": "execute_actions",
        "name": "Execute the Governed Actions",
        "variables": [],
        "app": " "
    })

    for app_name, action_list in actions.items():
        for action_code, action_name in action_list:
            variables = get_execution_variables(app_name, action_code)
            # only not None if the action has execution_codes function
            if variables:
                if app_name not in executable_actions:
                    executable_actions[app_name] = []
                executable_actions[app_name].append(
                    {
                        "value": action_code,
                        "name": get_action_name(app_name, action_code),
                        "variables": variables,
                        "app": app_name
                    }
                )

    return executable_actions

def load_entities(platform):
    from policyengine.utils import get_all_permissions
    SUPPORTED_ENTITIES = ["CommunityUser", "CommunityRole", "Permission", "SlackChannel", "CommunityDoc"]
    
    entities = {}
    # extract all readable names of CommunityUsers on this platform
    entities["CommunityUser"] = [{"name": user.readable_name, "value": user.username} for user in platform.get_users()]

    # extract all roles on this platform
    entities["CommunityRole"] = [{"name": role.role_name, "value": role.role_name } for role in platform.get_roles()]

    # extract all permissions on this platform
    entities["Permission"] = [{"name": permission.name, "value": permission.codename } for permission in get_all_permissions([platform.platform])]

    # extract all community documents on this platform
    entities["CommunityDoc"] = [{"name": document.name, "value": document.name } for document in platform.community.get_documents()]
    # extract all Slack channels in this platform
    if platform.platform.upper() == "SLACK":
        entities["SlackChannel"] = [
                            {
                                "name": channel.get("name", channel["id"]), 
                                "value": channel["id"]
                            } for channel in platform.get_conversations(types=["channel"])
                        ]
    return entities