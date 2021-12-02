from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def consider_proposed_actions():
    # import PK modules inside the task so we get code updates.
    from policyengine import engine
    from policyengine.models import Proposal, ExecutedActionTriggerAction

    pending_proposals = Proposal.objects.filter(status=Proposal.PROPOSED)
    for proposal in pending_proposals:
        logger.debug(f"Evaluating proposal '{proposal}'")
        try:
            engine.evaluate_proposal(proposal)
        except (engine.PolicyDoesNotExist, engine.PolicyIsNotActive, engine.PolicyDoesNotPassFilter) as e:
            logger.warn(f"ERROR {type(e).__name__} deleting proposal: {proposal}")
            new_proposal = engine.delete_and_rerun(proposal)
            logger.debug(f"New proposal: {new_proposal}")
        except Exception as e:
            logger.error(f"Error running proposal {proposal}: {repr(e)} {e}")

        if proposal.status == Proposal.PASSED:
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
