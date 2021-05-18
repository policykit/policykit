from __future__ import absolute_import, unicode_literals

import logging

from celery import shared_task
from django.utils import timezone
from django_db_logger.models import EvaluationLog
from policykit.settings import DB_LOG_EXPIRATION_HOURS

from policyengine.models import ConstitutionAction, PlatformAction, Proposal
from policyengine.views import execute_policy

logger = logging.getLogger(__name__)

@shared_task
def consider_proposed_actions():
    platform_actions = PlatformAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    logger.info(f"{platform_actions.count()} proposed PlatformActions")
    for action in platform_actions:
         #if they have execute permission, skip all policies
        if action.initiator.has_perm(action._meta.app_label + '.can_execute_' + action.action_codename):
            action.execute()
        else:
            for policy in action.community.get_platform_policies().filter(is_active=True):
                # Execute the most recently updated policy that passes filter()
                was_executed = execute_policy(policy, action, is_first_evaluation=False)
                if was_executed:
                    break

    """bundle_actions = PlatformActionBundle.objects.filter(proposal__status=Proposal.PROPOSED)
    for action in bundle_actions:
        #if they have execute permission, skip all policies

        if action.initiator.has_perm(action._meta.app_label + '.can_execute_' + action.action_codename):
            action.execute()
        else:
            for policy in action.community.get_platform_policies().filter(is_active=True):
                execute_policy(policy, action)"""

    constitution_actions = ConstitutionAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    logger.info(f"{constitution_actions.count()} proposed ConstitutionActions")
    for action in constitution_actions:
        #if they have execute permission, skip all policies
        if action.initiator.has_perm(action._meta.app_label + '.can_execute_' + action.action_codename):
            action.execute()
        else:
            for policy in action.community.get_constitution_policies().filter(is_active=True):
                # Execute the most recently updated policy that passes filter()
                was_executed = execute_policy(policy, action, is_first_evaluation=False)
                if was_executed:
                    break

    clean_up_logs()
    logger.info('finished task')


def clean_up_logs():
    hours_ago = timezone.now()-timezone.timedelta(hours=DB_LOG_EXPIRATION_HOURS)
    count,_ = EvaluationLog.objects.filter(create_datetime__lt=hours_ago).delete()
    if count:
        logger.info(f"Deleted {count} EvaluationLogs")
