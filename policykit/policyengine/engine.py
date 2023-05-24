import inspect
import logging
import sys
import traceback

from actstream import action as actstream_action

import policyengine.utils as Utils
from policyengine.safe_exec_code import execute_user_code

logger = logging.getLogger(__name__)
db_logger = logging.getLogger("db")

class AttrDict(dict):
    """
    For accessing variables using attribute-style access
    e.g. variables.slack_channel_id
    """
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

class EvaluationLogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        kwargs["extra"] = self.extra
        return (msg, kwargs)


class EvaluationContext:
    """
    Class to hold all variables available in a policy evaluation.
    All attributes on this class are in scope and can be used by the policy author.

    Attributes:
        proposal (Proposal): The proposal representing this evaluation.
        action (BaseAction): The action that triggered this policy evaluation.
        policy (Policy): The policy being evaluated.
        slack (SlackCommunity)
        discord (DiscordCommunity)
        discourse (DiscourseCommunity)
        reddit (RedditCommunity)
        github (GithubCommunity)
        opencollective (OpencollectiveCommunity)
        loomio (LoomioCommunity)
        sourcecred (SourcecredCommunity)
        metagov (Metagov): Metagov library for performing enabled actions and processes.
        logger (logging.Logger): Logger that will log messages to the PolicyKit web interface.
        variables (Policy.variables): Dict with policy variables keys and values
    """

    def __init__(self, proposal):
        from policyengine.metagov_client import Metagov
        from policyengine.models import ExecutedActionTriggerAction

        if isinstance(proposal.action, ExecutedActionTriggerAction):
            self.action = proposal.action.action
        else:
            self.action = proposal.action

        self.policy = proposal.policy
        self.variables = AttrDict()
        self.proposal = proposal

        # Can't use logger in filter step because proposal isn't saved yet
        if proposal.pk:
            self.logger = EvaluationLogAdapter(
                db_logger, {"community": self.action.community.community, "proposal": proposal}
            )

        from policyengine.models import Community, CommunityPlatform

        parent_community: Community = self.action.community.community

        for comm in CommunityPlatform.objects.filter(community=parent_community):
            for function_name in Utils.SHIMMED_PROPOSAL_FUNCTIONS:
                _shim_proposal_function(comm, proposal, function_name)
            # Make the CommunityPlatforms available in the evaluation context,
            # so policy author can access them as vars like "slack" and "opencollective"
            setattr(self, comm.platform, comm)

        self.metagov = Metagov(proposal)
               
         # Make policy variables available in the evaluation context
        setattr(self, "variables", AttrDict({ variable.name : variable.get_variable_values() for variable in self.policy.variables.all() or []}))



class PolicyEngineError(Exception):
    """Base class for exceptions raised from the policy engine"""

    pass


class PolicyCodeError(PolicyEngineError):
    """Raised when an exception is raised in a policy"""

    def __init__(self, step, message):
        self.step = step
        self.message = message
        super().__init__(self.message)


class PolicyDoesNotExist(PolicyEngineError):
    """Raised when trying to evaluate a Proposal where the policy has been deleted"""

    pass


class PolicyIsNotActive(PolicyEngineError):
    """Raised when trying to evaluate a Proposal where the policy has been marked inactive"""

    pass


class PolicyDoesNotPassFilter(PolicyEngineError):
    """Raised when trying to evaluate a Proposal where the action no longer passes the policy's filter step"""

    pass


def get_eligible_policies(action):
    from django.db.models import Q

    from policyengine.models import ExecutedActionTriggerAction, PolicyActionKind

    if action.kind == PolicyActionKind.TRIGGER:
        # Trigger policies MUST match the trigger action. There is no "base policy" concept for triggers.
        if isinstance(action, ExecutedActionTriggerAction):
            action_type_match = Q(action_types__codename=action.action.action_type)
        else:
            action_type_match = Q(action_types__codename=action.action_type)
    else:
        # Governing policies can match if they have NO action_types specified (meaning its the "base policy")
        action_type_match = Q(action_types=None) | Q(action_types__codename=action.action_type)

    eligible_policies = action.community.community.get_policies().filter(Q(kind=action.kind) & action_type_match)

    logger.debug(f"{action.kind} action '{action}' found {eligible_policies.count()} eligible policies")
    return eligible_policies


def evaluate_action(action):
    """
    Called the FIRST TIME that an action is evaluated.

    For governable actions ("platform" and "constitution"):
    - Get a list of eligible policies based on action_types. Raise an error if no policies match. There should always be a matching base policy from the starterkit.
    - Try each policy, executing only the Filter step. The first policy that returns True from the Filter step is the policy that will govern this action.
    - Evaluate the selected Policy. Create and save the Proposal for the evaluation, which will be re-evaluated from the celery task if it is pending

    For trigger actions:
    - Evaluate against all eligible policies
    - Save the Proposal for each evaluation, which will be re-evaluated from the celery task if it is pending
    """
    from policyengine.models import PolicyActionKind

    eligible_policies = get_eligible_policies(action)
    if not eligible_policies.exists():
        if action.kind != PolicyActionKind.TRIGGER:
            raise Exception(f"no eligible policies found for governable action '{action}'")
        else:
            return None

    # If this is a trigger action, evaluate ALL eligible policies
    if action.kind == PolicyActionKind.TRIGGER:
        proposals = []
        matching_policies_proposals = create_prefiltered_proposals(action, eligible_policies, allow_multiple=True)
        for proposal in matching_policies_proposals:
            try:
                evaluate_proposal(proposal, is_first_evaluation=True)
            except Exception as e:
                logger.debug(f"{proposal} raised exception {type(e).__name__} {e}")
                proposal.delete()
            else:
                proposals.append(proposal)
        return proposals

    # If this is a governable action, choose ONE policy to evaluate
    else:
        while eligible_policies.exists():
            proposal = create_prefiltered_proposals(action, eligible_policies)
            if not proposal:
                # This means that the action didn't pass the filter for ANY policies.
                logger.warn(f"Governable action {action} did not pass Filter for any eligible policies.")
                return None

            # Run the proposal
            try:
                evaluate_proposal(proposal, is_first_evaluation=True)
            except Exception as e:
                eligible_policies = eligible_policies.exclude(pk=proposal.policy.pk)
                logger.debug(f"{proposal} raised exception {type(e).__name__} {e}, choosing a different policy...")
                proposal.delete()
                pass
            else:
                return proposal


def create_prefiltered_proposals(action, policies, allow_multiple=False):
    """
    Evaluate action against the Filter step in all provided policies, and return the Proposal
    for the first Policy where the aciton passed the Filter.

    If allow_multiple is true, returns a *list* of all Proposals where the action passed the filter (used for Triggers).
    """
    from policyengine.models import Policy, Proposal

    proposals = []
    for policy in policies:
        proposal = Proposal(policy=policy, action=action, status=Proposal.PROPOSED)
        context = EvaluationContext(proposal)
        try:
            passed_filter = exec_code_block(policy.filter, context, Policy.FILTER)
        except Exception as e:
            # Log unhandled exception to the db, so policy author can view it in the UI.
            context.logger.error(f"Exception in 'filter': {str(e)}")
            # If there was an exception raised in 'filter', treat it as if the action didn't pass this policy's filter.
            continue

        if passed_filter:
            # Defer saving trigger actions and proposals until we need to, so we don't bloat the database
            if not action.pk:
                action.save()
            proposal.save()
            if allow_multiple:
                proposals.append(proposal)
            else:
                logger.debug(f"For action '{action}', choosing policy '{policy}'")
                return proposal

    if allow_multiple:
        return proposals
    else:
        logger.warn(f"No matching policy for {action}")
        return None


def delete_and_rerun(proposal):
    """
    Delete the proposal and re-run evaluate_action for the relevant action.
    Called when the proposal becomes invalid, because the policy was deleted or is no longer relevant.
    """
    action = proposal.action
    proposal.delete()
    new_evaluation = evaluate_action(action)
    return new_evaluation


def evaluate_proposal(proposal, is_first_evaluation=False):
    """
    Evaluate policy for given action. This can be run repeatedly to check proposed actions.
    """

    if not proposal.policy:
        # This could happen if the Policy has been deleted since the first proposal.
        raise PolicyDoesNotExist

    if not proposal.policy.is_active:
        raise PolicyIsNotActive

    context = EvaluationContext(proposal)

    try:
        return evaluate_proposal_inner(context, is_first_evaluation)
    except PolicyDoesNotPassFilter:
        # The policy changed so that the action no longer passes the 'filter' step
        raise
    except PolicyCodeError as e:
        # Log policy code exception to the db, so policy author can view it in the UI.
        logger.debug(str(e))
        context.logger.error(str(e))
        raise
    except Exception as e:
        # Log unhandled exception to the db, so policy author can view it in the UI.
        context.logger.error(f"Unhandled exception: {repr(e)} {e}")
        raise


def evaluate_proposal_inner(context: EvaluationContext, is_first_evaluation: bool):
    from policyengine.models import Policy, Proposal

    proposal = context.proposal
    action = proposal.action
    policy = proposal.policy

    logger.debug('*')
    logger.debug(action.__dict__)

    if not exec_code_block(policy.filter, context, Policy.FILTER):
        # logger.debug("does not pass filter")
        raise PolicyDoesNotPassFilter

    # If policy is being evaluated for the first time, run "initialize" block
    if is_first_evaluation:
        exec_code_block(policy.initialize, context, Policy.INITIALIZE)

    # Run "check" block of policy
    check_result = exec_code_block(policy.check, context, Policy.CHECK)
    check_result = sanitize_check_result(check_result) # sanitize so None becomes PROPOSED

    if is_first_evaluation or check_result != Proposal.PROPOSED:
        # log the check result for first evaluation, or if the proposal is newly completed
        context.logger.debug(f"Evaluating Proposal {proposal.pk}, check returned {check_result.upper()}")

    if check_result == Proposal.PASSED:
        logger.debug('Met PASS conditions!')
        # run "pass" block of policy
        exec_code_block(policy.success, context, Policy.SUCCESS)
        # mark proposal as 'passed'
        proposal._pass_evaluation()
        assert proposal.status == Proposal.PASSED

        if action._is_executable:
            action.execute()

    if check_result == Proposal.FAILED:
        # run "fail" block of policy
        exec_code_block(policy.fail, context, Policy.FAIL)
        # mark proposal as 'failed'
        proposal._fail_evaluation()
        assert proposal.status == Proposal.FAILED

    # Revert the action if necessary
    should_revert = (
        is_first_evaluation and check_result in [Proposal.PROPOSED, Proposal.FAILED] and action._is_reversible
    )

    if should_revert:
        context.logger.debug(f"Reverting action")
        action._revert()

    # If this action is moving into pending state for the first time, run the Notify block (to start a vote, maybe)
    if check_result == Proposal.PROPOSED and is_first_evaluation:
        actstream_action.send(
            action, verb="was proposed", community_id=action.community.id, action_codename=action.action_type
        )
        # Run "notify" block of policy
        exec_code_block(policy.notify, context, Policy.NOTIFY)

    return True


def exec_code_block(code_string: str, context: EvaluationContext, step_name="unknown"):
    """
    Execute a policy step with all the available context. Uses restricted safe execution
    to limit available modules.
    """
    # Each item on the EvaluationContext gets passed to the funciton as a keyword argument
    args = ", ".join(context.__dict__.keys())
    wrapper_start = f"def {step_name}({args}):\r\n"
    lines = ["  " + item for item in code_string.splitlines()]
    code = wrapper_start + "\r\n".join(lines)

    try:
        return execute_user_code(code, step_name, **context.__dict__)
    except SyntaxError as err:
        error_class = err.__class__.__name__
        detail = err.args[0]
        line_number = err.lineno
    except Exception as err:
        error_class = err.__class__.__name__
        detail = err.args[0]
        _, _, tb = sys.exc_info()
        line_number = traceback.extract_tb(tb)[-1][1]
    else:
        return
    if line_number is None:
        raise PolicyCodeError(step=step_name, message="%s in %s: %s" % (error_class, step_name, detail))
    else:
        raise PolicyCodeError(
            step=step_name, message="%s at line %d of %s: %s" % (error_class, line_number - 1, step_name, detail)
        )


def sanitize_check_result(res):
    from policyengine.models import Proposal

    if res in [Proposal.PROPOSED, Proposal.PASSED, Proposal.FAILED]:
        return res
    return Proposal.PROPOSED


def _shim_proposal_function(community_platform, proposal, function_name):
    """
    Shim functions that receive the proposal as the first argument.
    This makes it so the policy author doesn't need to pass the proposal themselves.

    For example, instead of:
    'slack.initiate_vote(proposal, text="please vote")'

    The policy author can write:
    'slack.initiate_vote(text="please vote")'
    """
    from policyengine.models import Proposal

    # skip if this community doesn't have this function defined
    if not hasattr(community_platform, function_name):
        return

    # store the original function that we will shim
    old_function = getattr(community_platform, function_name)

    # skip if this function doesn't expect 'parameter' as the first arg
    function_parameters = list(inspect.signature(old_function).parameters.values())
    if not len(function_parameters) > 1 and function_parameters[1].name == "proposal":
        return

    # create a shim function that passes the proposal
    def shim_function(*args, **kwargs):
        # If proposal was passed in by the policy author, remove it
        if len(args) > 0 and isinstance(args[0], Proposal):
            args = args[1:]
        if kwargs.get("proposal"):
            del kwargs["proposal"]

        old_function(proposal, *args, **kwargs)

    # set the new function on the community platform object
    setattr(community_platform, function_name, shim_function)
