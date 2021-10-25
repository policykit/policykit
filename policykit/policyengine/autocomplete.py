import inspect
from inspect import getmembers, isfunction, Parameter, signature
import policyengine.utils as Utils
from django.apps import apps

PROPOSAL_VARNAME = "proposal"
POLICY_VARNAME = "policy"
ACTION_VARNAME = "action"


def generate_platform_autocompletes():
    """
    Generate a dictionary with autocomplete strings for each function available on each CommunityPlatforms, like this:

    {
        "slack": ["slack.post_message(text, post_type='channel')", ...],
        "opencollective": ["opencollective.post_message(text, expense_id)", ...]
    }
    """
    from policyengine.models import CommunityPlatform

    integration_autocompletes = {}
    for app_name in Utils.get_platform_integrations():

        community_platform_classes = [
            c for c in apps.get_app_config(app_name).get_models() if issubclass(c, CommunityPlatform)
        ]
        if not community_platform_classes:
            continue
        cls = community_platform_classes[0]
        integration_autocompletes[app_name] = [f"{app_name}.{h}" for h in _get_function_hints(cls, app_name)]

    return integration_autocompletes


def _get_function_hints(cls, module_substring, excluded_functions=None):
    hints = []
    for (n, f) in getmembers(cls, isfunction):
        if not module_substring in f.__module__ or n.startswith("_") or n == "save":
            continue
        if excluded_functions and n in excluded_functions:
            continue
        sig = inspect.signature(f)
        params = []
        for param in sig.parameters.values():
            if param.name == "self":
                continue
            elif param.kind not in [Parameter.POSITIONAL_ONLY, Parameter.POSITIONAL_OR_KEYWORD]:
                continue
            elif param.default != Parameter.empty:
                # add quotes around string defaults
                d = f"'{param.default}'" if isinstance(param.default, str) else param.default
                params.append(f"{param.name}={d}")
            else:
                params.append(param.name)
        params_string = ", ".join(params)
        hint = f"{n}({params_string})"
        hints.append(hint)
    return hints


def generate_evaluation_autocompletes():
    """
    Generate autocomplete strings for proposal, policy, action, and logger
    """
    autocompletes = []

    ### PROPOSAL
    from policyengine.models import Proposal

    for f in Proposal._meta.get_fields(include_parents=False):
        if f.one_to_many:
            continue
        if f.name in ["id", "action", "policy"]:
            continue
        autocompletes.append(f"{PROPOSAL_VARNAME}.{f.name}")
    # add functions
    function_hints = _get_function_hints(
        Proposal, "policyengine", excluded_functions=["pass_evaluation", "fail_evaluation"]
    )
    autocompletes.extend([f"{PROPOSAL_VARNAME}.{h}" for h in function_hints])

    ### POLICY
    fields = ["name", "description", "modified_at", "community"]
    autocompletes.extend([f"{POLICY_VARNAME}.{f}" for f in fields])

    ### ACTION
    fields = ["action_type", "initiator", "community"]
    autocompletes.extend([f"{ACTION_VARNAME}.{f}" for f in fields])

    ### LOGGER
    autocompletes.extend(["logger", "logger.debug()", "logger.info()", "logger.warn()", "logger.error()"])
    return autocompletes


integration_autocompletes = generate_platform_autocompletes()
general_autocompletes = generate_evaluation_autocompletes()