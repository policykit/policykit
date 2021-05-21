from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task
from django.utils import timezone
from django_db_logger.models import EvaluationLog
from policykit.settings import DB_LOG_EXPIRATION_HOURS

from policyengine.models import ConstitutionAction, PlatformAction, Proposal
from policyengine.views import govern_action

logger = logging.getLogger(__name__)

@shared_task
def consider_proposed_actions():
    platform_actions = PlatformAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    logger.info(f"{platform_actions.count()} proposed PlatformActions")
    for action in platform_actions:
        govern_action(action, is_first_evaluation=False)

    """bundle_actions = PlatformActionBundle.objects.filter(proposal__status=Proposal.PROPOSED)
    for action in bundle_actions:
        govern_action(action, is_first_evaluation=False)"""

    constitution_actions = ConstitutionAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    logger.info(f"{constitution_actions.count()} proposed ConstitutionActions")
    for action in constitution_actions:
        govern_action(action, is_first_evaluation=False)

    clean_up_logs()
    logger.info('finished task')


def clean_up_logs():
    hours_ago = timezone.now()-timezone.timedelta(hours=DB_LOG_EXPIRATION_HOURS)
    count,_ = EvaluationLog.objects.filter(create_datetime__lt=hours_ago).delete()
    if count:
        logger.info(f"Deleted {count} EvaluationLogs")
