import logging

from actstream import action as actstream_action
from django.conf import settings

from policyengine.utils import ActionKind

logger = logging.getLogger(__name__)
db_logger = logging.getLogger("db")


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


def evaluation_logger(proposal, level="DEBUG"):
    """
    Get a logging function that logs to the database. Logs are visible to the community members at /logs.
    """
    level_num = getattr(logging, level)

    def log(msg):
        context = {"community": proposal.action.community.community, "proposal": proposal}
        db_logger.log(level_num, str(msg), context)

        message = f"[{proposal.action} ({proposal.action.pk})][{proposal.policy} ({proposal.policy.pk})] {msg}"
        logger.log(level_num, message)

    return log


def govern_action(action):
    """
    Called the FIRST TIME that an action is evaluated.
    - If the initiator has "can execute" permission, execute the action and mark it as "passed."
    - Otherwise, choose a Policy to evaluate.
    - Create a Proposal and run it.
    """
    from policyengine.models import (
        ConstitutionAction,
        ConstitutionActionBundle,
        PlatformAction,
        PlatformActionBundle,
        Proposal,
    )

    # if they have execute permission, skip all policies
    if action.initiator.has_perm(f"{action._meta.app_label}.can_execute_{action.action_type}"):
        action.execute()
        # No `Proposal` is created because we don't evaluate it
    else:
        eligible_policies = None
        if isinstance(action, PlatformAction) or isinstance(action, PlatformActionBundle):
            eligible_policies = action.community.get_platform_policies().filter(is_active=True)
        elif isinstance(action, ConstitutionAction) or isinstance(action, ConstitutionActionBundle):
            eligible_policies = action.community.get_constitution_policies().filter(is_active=True)
        else:
            raise Exception("govern_action: unrecognized action")

        existing_proposals = Proposal.objects.filter(action=action)
        if existing_proposals:
            logger.warn(f"There are already {existing_proposals.count()} proposals for action {action}")

        while eligible_policies.exists():
            # logger.debug(f"choosing from {eligible_policies.count()} eligible policies")
            proposal = choose_policy(action, eligible_policies)
            if not proposal:
                # This means that the action didn't pass the filter for ANY policies.
                return None

            # Run the proposal
            try:
                evaluate_proposal(proposal, is_first_evaluation=True)
            except Exception as e:
                eligible_policies = eligible_policies.exclude(pk=proposal.policy.pk)
                logger.debug(f"{proposal} raised a exception '{e}', choosing a different policy...")
                proposal.delete()
                pass
            else:
                return proposal


def choose_policy(action, policies):
    from policyengine.models import Policy, Proposal

    for policy in policies:
        proposal = Proposal.objects.create(policy=policy, action=action, status=Proposal.PROPOSED)
        try:
            passed_filter = exec_code_block(policy.filter, Policy.FILTER, proposal)
        except Exception as e:
            # Log unhandled exception to the db, so policy author can view it in the UI.
            error = evaluation_logger(proposal, level="ERROR")
            error("Exception: " + str(e))
            proposal.delete()
            # If there was an exception raised in 'filter', treat it as if the action didn't pass this policy's filter.
            continue

        if passed_filter:
            logger.debug(f"For action '{action}', choosing policy '{policy}'")
            # proposal.save()
            return proposal

        proposal.delete()

    logger.debug(f"For action {action}, no matching policy found!")


def delete_and_rerun(proposal):
    """
    Delete the proposal and re-run govern_action for the relevant action.
    Called when the proposal becomes invalid, because the policy was deleted or is no longer relevant.
    """
    action = proposal.action
    proposal.delete()
    new_evaluation = govern_action(action)
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

    try:
        return evaluate_proposal_inner(proposal, is_first_evaluation)
    except PolicyDoesNotPassFilter:
        # The policy changed so that the action no longer passes the 'filter' step
        raise
    except PolicyCodeError as e:
        # Log policy code exception to the db, so policy author can view it in the UI.
        error = evaluation_logger(proposal, level="ERROR")
        error(f"Exception raised in '{e.step}' block: {e.message}")
        raise
    except Exception as e:
        # Log unhandled exception to the db, so policy author can view it in the UI.
        error = evaluation_logger(proposal, level="ERROR")
        error("Unhandled exception: " + str(e))
        raise


def evaluate_proposal_inner(proposal, is_first_evaluation: bool):
    from policyengine.models import ConstitutionAction, PlatformAction, Policy, Proposal

    policy = proposal.policy
    action = proposal.action
    debug = evaluation_logger(proposal)

    if not exec_code_block(policy.filter, Policy.FILTER, proposal):
        raise PolicyDoesNotPassFilter

    optional_args = {}
    if settings.METAGOV_ENABLED:
        from integrations.metagov.library import Metagov

        optional_args["metagov"] = Metagov(proposal)

    # If policy is being evaluated for the first time, initialize it
    if is_first_evaluation:
        # debug(f"Initializing")
        # run "initialize" block of policy
        exec_code_block(policy.initialize, Policy.INITIALIZE, proposal, **optional_args)

    # Run "check" block of policy
    check_result = exec_code_block(policy.check, Policy.CHECK, proposal, **optional_args)
    check_result = sanitize_check_result(check_result)
    debug(f"Check returned '{check_result}'")

    if check_result == Proposal.PASSED:
        # run "pass" block of policy
        exec_code_block(policy.success, Policy.SUCCESS, proposal, **optional_args)
        # debug(f"Executed pass block of policy")
        # mark proposal as 'passed'
        proposal.pass_evaluation()
        assert proposal.status == Proposal.PASSED

        # EXECUTE the action if....
        # it is a PlatformAction that was proposed in the PolicyKit UI
        if action.action_kind == ActionKind.PLATFORM and not action.community_origin:
            action.execute()
        # it is a constitution action
        elif action.action_kind == ActionKind.CONSTITUTION:
            action.execute()

        if settings.METAGOV_ENABLED:
            # Close pending process if exists (does nothing if process was already closed)
            optional_args["metagov"].close_process()

    if check_result == Proposal.FAILED:
        # run "fail" block of policy
        exec_code_block(policy.fail, Policy.FAIL, proposal, **optional_args)
        # debug(f"Executed fail block of policy")
        # mark proposal as 'failed'
        proposal.fail_evaluation()
        assert proposal.status == Proposal.FAILED

        if settings.METAGOV_ENABLED:
            # Close pending process if exists (does nothing if process was already closed)
            optional_args["metagov"].close_process()

    # Revert the action if necessary
    should_revert = (
        is_first_evaluation
        and check_result in [Proposal.PROPOSED, Proposal.FAILED]
        and action.action_kind == ActionKind.PLATFORM
        and action.community_origin
    )

    if should_revert:
        debug(f"Reverting action")
        action.revert()

    # If this action is moving into pending state for the first time, run the Notify block (to start a vote, maybe)
    if check_result == Proposal.PROPOSED and is_first_evaluation:
        actstream_action.send(
            action, verb="was proposed", community_id=action.community.id, action_codename=action.action_type
        )
        # Run "notify" block of policy
        debug(f"Notifying")
        exec_code_block(policy.notify, Policy.NOTIFY, proposal, **optional_args)

    return True


def exec_code_block(code_string: str, step_name: str, proposal, metagov=None):
    from policyengine.models import CommunityUser

    action = proposal.action
    policy = proposal.policy
    users = CommunityUser.objects.filter(community=policy.community)
    debug = evaluation_logger(proposal)

    _locals = locals()
    _globals = globals()

    wrapper_start = "def func(proposal, policy, action, users, debug, metagov):\r\n"
    wrapper_start += "  PASSED = 'passed'\r\n  FAILED = 'failed'\r\n  PROPOSED = 'proposed'\r\n"

    wrapper_end = "\r\nresult = func(proposal, policy, action, users, debug, metagov)"

    try:
        exec_code(code_string, wrapper_start, wrapper_end, None, _locals)
    except Exception as e:
        logger.exception(f"Got exception in exec_code {step_name} step:")
        raise PolicyCodeError(step=step_name, message=str(e))

    return _locals.get("result")


def exec_code(code, wrapperStart, wrapperEnd, globals=None, locals=None):
    lines = ["  " + item for item in code.splitlines()]
    code = wrapperStart + "\r\n".join(lines) + wrapperEnd
    exec(code, globals, locals)


def sanitize_check_result(res):
    from policyengine.models import Proposal

    if res in [Proposal.PROPOSED, Proposal.PASSED, Proposal.FAILED]:
        return res
    return Proposal.PROPOSED
