from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def evaluate_pending_proposals():
    """
    Iterates through all pending Proposals and re-evaluates them.
    """
    # import PK modules inside the task so we get code updates.
    from policyengine import engine
    from policyengine.models import Proposal, ExecutedActionTriggerAction, GovernableAction


    pending_proposals = Proposal.objects.filter(status=Proposal.PROPOSED)
    #logger.debug("Running evaluate_pending_proposals:" + str(len(pending_proposals)))

    for proposal in pending_proposals:
        try:
            community_name = proposal.action.community.community_name
        except Exception as e:
            logger.error(f"Error getting community name for proposal {proposal}: {repr(e)} {e}")
            continue
        logger.debug(f"{community_name} - Evaluating proposal '{proposal}'")
        try:
            engine.evaluate_proposal(proposal)
        except (engine.PolicyDoesNotExist, engine.PolicyIsNotActive, engine.PolicyDoesNotPassFilter) as e:
            logger.warn(f"{community_name} - ERROR - {type(e).__name__} deleting proposal: {proposal}")
            new_proposal = engine.delete_and_rerun(proposal)
            logger.debug(f"{community_name} - New proposal: {new_proposal}")
        except Exception as e:
            logger.error(f"{community_name} - Error running proposal {proposal}: {repr(e)} {e}")
            
            
        # If the engine just PASSED a GovernableAction, generate a new Trigger for the newly executed action.
        # This lets us use GovernableActions as triggers for trigger policies.
        if proposal.status == Proposal.PASSED and isinstance(proposal.action, GovernableAction):
            ExecutedActionTriggerAction.from_action(proposal.action).evaluate()

    clean_up_logs()
    # logger.debug("finished task")


def clean_up_logs():
    from django_db_logger.models import EvaluationLog
    from policykit.settings import DB_MAX_LOGS_TO_KEEP

    expired_logs = EvaluationLog.objects.filter(
        pk__in=EvaluationLog.objects.all().order_by("-create_datetime").values_list("pk")[DB_MAX_LOGS_TO_KEEP:]
    )

    if expired_logs.exists():
        # logger.debug(f"Deleting {expired_logs.count()} EvaluationLogs")
        expired_logs.delete()
