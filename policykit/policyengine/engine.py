import logging

from actstream import action as actstream_action
from django.conf import settings

logger = logging.getLogger(__name__)
db_logger = logging.getLogger("db")


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
        metagov (Metagov): Metagov library for performing enabled actions and processes.
        logger (logging.Logger): Logger that will log messages to the PolicyKit web interface.

    """

    def __init__(self, proposal):
        from policyengine.models import ExecutedActionTriggerAction

        if isinstance(proposal.action, ExecutedActionTriggerAction):
            self.action = proposal.action.action
        else:
            self.action = proposal.action

        self.policy = proposal.policy
        self.proposal = proposal

        # Can't use logger in filter step because proposal isn't saved yet
        if proposal.pk:
            self.logger = EvaluationLogAdapter(
                db_logger, {"community": self.action.community.community, "proposal": proposal}
            )

        from policyengine.models import Community, CommunityPlatform

        parent_community: Community = self.action.community.community

        # Make all CommunityPlatforms available in the evaluation context
        for comm in CommunityPlatform.objects.filter(community=parent_community):
            setattr(self, comm.platform, comm)

        if settings.METAGOV_ENABLED:
            from integrations.metagov.library import Metagov

            self.metagov = Metagov(proposal)


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
    from policyengine.models import PolicyActionKind, ExecutedActionTriggerAction

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
    from policyengine.models import Proposal, PolicyActionKind

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
    Evaluate aciton against the Filter step in all provided policies, and return the Proposal
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
        context.logger.error(f"Exception raised in '{e.step}' block: {e.message}")
        raise
    except Exception as e:
        # Log unhandled exception to the db, so policy author can view it in the UI.
        context.logger.error("Unhandled exception: " + str(e))
        raise


def evaluate_proposal_inner(context: EvaluationContext, is_first_evaluation: bool):
    from policyengine.models import Policy, Proposal, PolicyActionKind

    proposal = context.proposal
    action = proposal.action
    policy = proposal.policy

    if not exec_code_block(policy.filter, context, Policy.FILTER):
        logger.debug("does not pass filter")
        raise PolicyDoesNotPassFilter

    # If policy is being evaluated for the first time, initialize it
    if is_first_evaluation:
        # run "initialize" block of policy
        exec_code_block(policy.initialize, context, Policy.INITIALIZE)

    # Run "check" block of policy
    check_result = exec_code_block(policy.check, context, Policy.CHECK)
    check_result = sanitize_check_result(check_result)
    context.logger.debug(f"Check returned '{check_result}'")

    if check_result == Proposal.PASSED:
        # run "pass" block of policy
        exec_code_block(policy.success, context, Policy.SUCCESS)
        # mark proposal as 'passed'
        proposal.pass_evaluation()
        assert proposal.status == Proposal.PASSED

        if action.is_executable:
            action.execute()

        if settings.METAGOV_ENABLED:
            # Close pending process if exists (does nothing if process was already closed)
            context.metagov.close_process()

    if check_result == Proposal.FAILED:
        # run "fail" block of policy
        exec_code_block(policy.fail, context, Policy.FAIL)
        # mark proposal as 'failed'
        proposal.fail_evaluation()
        assert proposal.status == Proposal.FAILED

        if settings.METAGOV_ENABLED:
            # Close pending process if exists (does nothing if process was already closed)
            context.metagov.close_process()

    # Revert the action if necessary
    should_revert = (
        is_first_evaluation and check_result in [Proposal.PROPOSED, Proposal.FAILED] and action.is_reversible
    )

    if should_revert:
        context.logger.debug(f"Reverting action")
        action.revert()

    # If this action is moving into pending state for the first time, run the Notify block (to start a vote, maybe)
    if check_result == Proposal.PROPOSED and is_first_evaluation:
        actstream_action.send(
            action, verb="was proposed", community_id=action.community.id, action_codename=action.action_type
        )
        # Run "notify" block of policy
        context.logger.debug(f"Notifying")
        exec_code_block(policy.notify, context, Policy.NOTIFY)

    return True


def exec_code_block(code_string: str, context: EvaluationContext, step_name="unknown"):
    wrapper_start = "def func():\r\n"
    lines = ["  " + item for item in code_string.splitlines()]
    wrapper_end = "\r\nresult = func()"
    code = wrapper_start + "\r\n".join(lines) + wrapper_end

    try:
        return exec_code(code, context)
    except Exception as e:
        logger.exception(f"Got exception in exec_code {step_name} step:")
        raise PolicyCodeError(step=step_name, message=str(e))


def exec_code(code, context: EvaluationContext):
    PASSED, FAILED, PROPOSED = "passed", "failed", "proposed"
    _locals = locals().copy()
    # Add all attributes on EvaluationContext to scope
    _locals.update(context.__dict__)
    # Remove some variables from scope
    _locals.pop("code")
    _locals.pop("context")

    exec(code, _locals, _locals)
    return _locals.get("result")


def sanitize_check_result(res):
    from policyengine.models import Proposal

    if res in [Proposal.PROPOSED, Proposal.PASSED, Proposal.FAILED]:
        return res
    return Proposal.PROPOSED
