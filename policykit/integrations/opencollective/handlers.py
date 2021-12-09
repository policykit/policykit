import logging
import json

from django.dispatch import receiver
from integrations.opencollective.models import (
    ExpenseApproved,
    ExpenseCreated,
    ExpenseDeleted,
    ExpensePaid,
    ExpenseRejected,
    ExpenseUnapproved,
    OpencollectiveCommunity,
    OpencollectiveUser,
)
from metagov.core.signals import governance_process_updated, platform_event_created
from metagov.plugins.opencollective.models import OpenCollective, OpenCollectiveVote

logger = logging.getLogger(__name__)


@receiver(platform_event_created, sender=OpenCollective)
def opencollective_event_receiver(sender, instance, event_type, data, initiator, **kwargs):
    logger.debug(f"Received {event_type} event from {instance}")
    # logger.debug(data)
    if initiator.get("is_metagov_bot") == True:
        return
    try:
        opencollective_community = OpencollectiveCommunity.objects.get(
            team_id=instance.community_platform_id, community__metagov_slug=instance.community.slug
        )
    except OpencollectiveCommunity.DoesNotExist:
        logger.warn(f"No OpencollectiveCommunity matches {instance}")
        return

    trigger_action = None

    if event_type == "expense_created":
        trigger_action = ExpenseCreated(data=data)
    elif event_type == "expense_rejected":
        trigger_action = ExpenseRejected(data=data)
    elif event_type == "expense_approved":
        trigger_action = ExpenseApproved(data=data)
    elif event_type == "expense_deleted":
        trigger_action = ExpenseDeleted(data=data)
    elif event_type == "expense_unapproved":
        trigger_action = ExpenseUnapproved(data=data)
    elif event_type == "expense_paid":
        trigger_action = ExpensePaid(data=data)

    if not trigger_action:
        return None

    trigger_action.community = opencollective_community

    # Get or create the Open Collective user that initiated the trigger
    oc_username = initiator.get("user_id")
    if oc_username:
        user, _ = OpencollectiveUser.objects.get_or_create(
            username=oc_username,
            readable_name=oc_username,
            community=opencollective_community,
        )
        trigger_action.initiator = user

    trigger_action.evaluate()


@receiver(governance_process_updated, sender=OpenCollectiveVote)
def opencollective_vote_updated_receiver(sender, instance, status, outcome, errors, **kwargs):
    pass
