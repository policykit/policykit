from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task
from django.utils import timezone


logger = logging.getLogger(__name__)


@shared_task
def consider_proposed_actions():
    # import PK modules inside the task so we get code updates.
    from policyengine import engine, PolicyDoesNotPassFilter, PolicyDoesNotExist
    from policyengine.models import PolicyEvaluation

    pending_evaluations = PolicyEvaluation.objects.filter(status=PolicyEvaluation.PROPOSED)
    logger.debug(f"{pending_evaluations.count()} pending evaluations")
    for evaluation in pending_evaluations:

        logger.debug(f"Running evaluation for {evaluation}")
        try:
            # TODO: what if initiator has fotten .can_execute perms since first eval?
            engine.run_evaluation(evaluation)
        except PolicyDoesNotExist as e:
            logger.warn(f"PolicyEvaluation is no longer valid because the policy has been deleted.")
            new_evaluation = engine.delete_and_rerun(evaluation)
            logger.debug(f"New evaluation: {new_evaluation}")
        except PolicyDoesNotPassFilter as e:
            # This policy is no longer applicable, so we delete the eavluation and choose a new policy
            logger.warn(f"PolicyEvaluation is no longer valid because the action does not pass the policy filter.")
            new_evaluation = engine.delete_and_rerun(evaluation)
            logger.debug(f"New evaluation: {new_evaluation}")
        except Exception as e:
            logger.error(f"Error running evaluation {evaluation}: {e}")

    clean_up_logs()
    logger.debug("finished task")


def clean_up_logs():
    from policykit.settings import DB_LOG_EXPIRATION_HOURS
    from django_db_logger.models import EvaluationLog

    hours_ago = timezone.now() - timezone.timedelta(hours=DB_LOG_EXPIRATION_HOURS)
    count, _ = EvaluationLog.objects.filter(create_datetime__lt=hours_ago).delete()
    if count:
        logger.debug(f"Deleted {count} EvaluationLogs")
