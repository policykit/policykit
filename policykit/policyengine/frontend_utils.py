import policyengine.utils as Utils
from django.apps import apps

def get_filter_parameters(app_name, action_codename):
    """
        Get the designated filter parameters for a GovernableAction
    """
    action_model = apps.get_model(app_name, action_codename)
    if hasattr(action_model, "FILTER_PARAMETERS"):
        return action_model.FILTER_PARAMETERS
    else:
        return []
    
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
                base_action_list.append((action_code, verbose_name))
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
                    "variables": filter.loads("variables")
                })
    return filter_modules