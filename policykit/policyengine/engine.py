import logging

from actstream import action as actstream_action
from django.conf import settings

logger = logging.getLogger(__name__)
db_logger = logging.getLogger("db")

# define Python user-defined exceptions
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
    """Raised when trying to evaluate a PolicyEvaluation where the policy has been deleted"""

    pass


class PolicyDoesNotPassFilter(PolicyEngineError):
    """Raised when trying to evaluate a PolicyEvaluation where the action no longer passes the policy's filter step"""

    pass


def evaluation_logger(evaluation, level="DEBUG"):
    """
    Get a logging function that logs to the database. Logs are visible to the community members at /logs.
    """
    level_num = getattr(logging, level)

    def log(msg):
        context = {"community": evaluation.action.community.community, "evaluation": evaluation}
        db_logger.log(level_num, str(msg), context)

        message = f"[{evaluation.action} ({evaluation.action.pk})][{evaluation.policy} ({evaluation.policy.pk})] {msg}"
        logger.log(level_num, message)

    return log


def govern_action(action):
    """
    Called the FIRST TIME that an action is evaluated.
    - If the initiator has "can execute" permission, execute the action and mark it as "passed."
    - Otherwise, choose a Policy to evaluate.
    - Create a PolicyEvaluation and run it.
    """
    from policyengine.models import (
        PolicyEvaluation,
        PlatformAction,
        PlatformActionBundle,
        ConstitutionAction,
        ConstitutionActionBundle,
    )

    # if they have execute permission, skip all policies
    if action.initiator.has_perm(action._meta.app_label + ".can_execute_" + action.action_codename):
        action.execute()
        # No `PolicyEvaluation` is created because we don't evaluate it
    else:
        eligible_policies = None
        if isinstance(action, PlatformAction) or isinstance(action, PlatformActionBundle):
            eligible_policies = action.community.get_platform_policies().filter(is_active=True)
        elif isinstance(action, ConstitutionAction) or isinstance(action, ConstitutionActionBundle):
            eligible_policies = action.community.get_constitution_policies().filter(is_active=True)
        else:
            raise Exception("govern_action: unrecognized action")

        existing_evaluations = PolicyEvaluation.objects.filter(action=action)
        if existing_evaluations:
            logger.warn(f"There are already {existing_evaluations.count()} evaluations for action {action}")

        while eligible_policies.exists():
            # logger.debug(f"choosing from {eligible_policies.count()} eligible policies")
            evaluation = choose_policy(action, eligible_policies)
            if not evaluation:
                # This means that the action didn't pass the filter for ANY policies.
                return None

            # Run the evaluation
            try:
                run_evaluation(evaluation, is_first_evaluation=True)
            except Exception as e:
                eligible_policies = eligible_policies.exclude(pk=evaluation.policy.pk)
                logger.debug(f"{evaluation} raised a exception '{e}', choosing a different policy...")
                evaluation.delete()
                pass
            else:
                return evaluation


def choose_policy(action, policies):
    from policyengine.models import PolicyEvaluation, Policy

    for policy in policies:
        evaluation = PolicyEvaluation.objects.create(policy=policy, action=action, status=PolicyEvaluation.PROPOSED)
        try:
            passed_filter = _exec_code_block(policy.filter, Policy.FILTER, evaluation)
        except Exception as e:
            # Log unhandled exception to the db, so policy author can view it in the UI.
            error = evaluation_logger(evaluation, level="ERROR")
            error("Exception: " + str(e))
            evaluation.delete()
            # If there was an exception raised in 'filter', treat it as if the action didn't pass this policy's filter.
            continue

        if passed_filter:
            logger.debug(f"For action '{action}', choosing policy '{policy}'")
            # evaluation.save()
            return evaluation

        evaluation.delete()

    logger.debug(f"For action {action}, no matching policy found!")


def delete_and_rerun(evaluation):
    """
    Delete the evaluation and re-run govern_action for the relevant action.
    Called when the evaluation becomes invalid, because the policy was deleted or is no longer relevant.
    """
    action = evaluation.action
    evaluation.delete()
    new_evaluation = govern_action(action)
    return new_evaluation


def run_evaluation(evaluation, is_first_evaluation=False):
    """
    Evaluate policy for given action. This can be run repeatedly to check proposed actions.
    """

    if not evaluation.policy:
        # This could happen if the Policy has been deleted since the first evaluation.
        raise PolicyDoesNotExist

    try:
        return _execute_policy(evaluation, is_first_evaluation)
    except PolicyDoesNotPassFilter:
        # The policy changed so that the action no longer passes the 'filter' step
        raise
    except PolicyCodeError as e:
        # Log policy code exception to the db, so policy author can view it in the UI.
        error = evaluation_logger(evaluation, level="ERROR")
        error(f"Exception raised in '{e.step}' block: {e.message}")
        raise
    except Exception as e:
        # Log unhandled exception to the db, so policy author can view it in the UI.
        error = evaluation_logger(evaluation, level="ERROR")
        error("Unhandled exception: " + str(e))
        raise


def _execute_policy(evaluation, is_first_evaluation: bool):
    from policyengine.models import PolicyEvaluation, ConstitutionAction, PlatformAction, Policy

    policy = evaluation.policy
    action = evaluation.action
    debug = evaluation_logger(evaluation)
    
    if not _exec_code_block(policy.filter, Policy.FILTER, evaluation):
        raise PolicyDoesNotPassFilter

    optional_args = {}
    if settings.METAGOV_ENABLED:
        from integrations.metagov.library import Metagov

        optional_args["metagov"] = Metagov(evaluation)

    # If policy is being evaluated for the first time, initialize it
    if is_first_evaluation:
        # debug(f"Initializing")
        # run "initialize" block of policy
        _exec_code_block(policy.initialize, Policy.INITIALIZE, evaluation, **optional_args)

    # Run "check" block of policy
    check_result = _exec_code_block(policy.check, Policy.CHECK, evaluation, **optional_args)
    check_result = sanitize_check_result(check_result)
    debug(f"Check returned '{check_result}'")

    if check_result == PolicyEvaluation.PASSED:
        # run "pass" block of policy
        _exec_code_block(policy.success, Policy.SUCCESS, evaluation, **optional_args)
        # debug(f"Executed pass block of policy")
        # mark evaluation as 'passed'
        evaluation.pass_action()
        assert evaluation.status == PolicyEvaluation.PASSED

        # EXECUTE the action if....
        # it is a PlatformAction that was proposed in the PolicyKit UI
        if issubclass(type(action), PlatformAction) and not action.community_origin:
            action.execute()
        # it is a constitution action
        elif issubclass(type(action), ConstitutionAction):
            action.execute()

        if settings.METAGOV_ENABLED:
            # Close pending process if exists (does nothing if process was already closed)
            optional_args["metagov"].close_process()

    if check_result == PolicyEvaluation.FAILED:
        # run "fail" block of policy
        _exec_code_block(policy.fail, Policy.FAIL, evaluation, **optional_args)
        # debug(f"Executed fail block of policy")
        # mark evaluation as 'failed'
        evaluation.fail_action()
        assert evaluation.status == PolicyEvaluation.FAILED

        if settings.METAGOV_ENABLED:
            # Close pending process if exists (does nothing if process was already closed)
            optional_args["metagov"].close_process()

    # Revert the action if necessary
    should_revert = (
        is_first_evaluation
        and check_result in [PolicyEvaluation.PROPOSED, PolicyEvaluation.FAILED]
        and issubclass(type(action), PlatformAction)
        and action.community_origin
    )

    if should_revert:
        debug(f"Reverting action")
        action.revert()

    # If this action is moving into pending state for the first time, run the Notify block (to start a vote, maybe)
    if check_result == PolicyEvaluation.PROPOSED and is_first_evaluation:
        actstream_action.send(
            action, verb="was proposed", community_id=action.community.id, action_codename=action.action_codename
        )
        # Run "notify" block of policy
        debug(f"Notifying")
        _exec_code_block(policy.notify, Policy.NOTIFY, evaluation, **optional_args)

    return True


def _exec_code_block(code_string: str, step_name: str, evaluation, metagov=None):
    from policyengine.models import CommunityUser

    action = evaluation.action
    policy = evaluation.policy
    users = CommunityUser.objects.filter(community=policy.community)
    debug = evaluation_logger(evaluation)

    _locals = locals()
    _globals = globals()

    wrapper_start = "def func(evaluation, policy, action, users, debug, metagov):\r\n"
    wrapper_start += "  PASSED = 'passed'\r\n  FAILED = 'failed'\r\n  PROPOSED = 'proposed'\r\n"

    wrapper_end = "\r\nresult = func(evaluation, policy, action, users, debug, metagov)"

    try:
        _exec_code(code_string, wrapper_start, wrapper_end, None, _locals)
    except Exception as e:
        logger.exception(f"Got exception in exec_code {step_name} step:")
        raise PolicyCodeError(step=step_name, message=str(e))

    return _locals.get("result")


def _exec_code(code, wrapperStart, wrapperEnd, globals=None, locals=None):
    lines = ["  " + item for item in code.splitlines()]
    code = wrapperStart + "\r\n".join(lines) + wrapperEnd
    exec(code, globals, locals)


def sanitize_check_result(res):
    from policyengine.models import PolicyEvaluation

    if res in [PolicyEvaluation.PROPOSED, PolicyEvaluation.PASSED, PolicyEvaluation.FAILED]:
        return res
    return PolicyEvaluation.PROPOSED