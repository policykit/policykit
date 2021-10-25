import inspect
from inspect import getmembers, isfunction, Parameter
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

        autocompletes = []
        for (n, f) in getmembers(cls, isfunction):
            if app_name in f.__module__ and not n.startswith("_"):
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
                hint = f"{app_name}.{n}({params_string})"
                autocompletes.append(hint)

        integration_autocompletes[app_name] = autocompletes
    return integration_autocompletes


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