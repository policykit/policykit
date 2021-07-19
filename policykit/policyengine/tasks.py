from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task
from django.utils import timezone


logger = logging.getLogger(__name__)


@shared_task
def consider_proposed_actions():
    # import PK modules inside the task so we get code updates.
    from policyengine.views import govern_action
    from policyengine.models import ConstitutionAction, PlatformAction, Proposal

    platform_actions = PlatformAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    logger.debug(f"{platform_actions.count()} proposed PlatformActions")
    for action in platform_actions:
        govern_action(action, is_first_evaluation=False)

    """bundle_actions = PlatformActionBundle.objects.filter(proposal__status=Proposal.PROPOSED)
    for action in bundle_actions:
        govern_action(action, is_first_evaluation=False)"""

    constitution_actions = ConstitutionAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    logger.debug(f"{constitution_actions.count()} proposed ConstitutionActions")
    for action in constitution_actions:
        govern_action(action, is_first_evaluation=False)

    clean_up_logs()
    logger.debug("finished task")


def clean_up_logs():
    from policykit.settings import DB_LOG_EXPIRATION_HOURS
    from django_db_logger.models import EvaluationLog

    hours_ago = timezone.now() - timezone.timedelta(hours=DB_LOG_EXPIRATION_HOURS)
    count, _ = EvaluationLog.objects.filter(create_datetime__lt=hours_ago).delete()
    if count:
        logger.debug(f"Deleted {count} EvaluationLogs")
