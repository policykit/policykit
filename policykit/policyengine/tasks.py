from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task
from django.utils import timezone

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
            logger.error(f"Error running proposal {proposal}: {e}")

        if proposal.status == Proposal.PASSED:
            ExecutedActionTriggerAction.from_action(proposal.action).evaluate()

    clean_up_logs()
    logger.debug("finished task")


def clean_up_logs():
    from django_db_logger.models import EvaluationLog
    from policykit.settings import DB_LOG_EXPIRATION_HOURS

    hours_ago = timezone.now() - timezone.timedelta(hours=DB_LOG_EXPIRATION_HOURS)
    count, _ = EvaluationLog.objects.filter(create_datetime__lt=hours_ago).delete()
    if count:
        logger.debug(f"Deleted {count} EvaluationLogs")
