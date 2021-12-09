import logging

import integrations.discord.utils as DiscordUtils
from django.dispatch import receiver
from integrations.slack.models import DiscordCommunity, DiscordUser
from metagov.core.signals import governance_process_updated, platform_event_created
from metagov.plugins.discord.models import Discord
from policyengine.models import (
    BooleanVote,
    NumberVote,
    Proposal,
    ChoiceVote,
)

logger = logging.getLogger(__name__)

"""
Django signal handlers
"""


@receiver(platform_event_created, sender=Discord)
def slack_event_receiver(sender, instance, event_type, data, initiator, **kwargs):
    logger.debug(f"Received {event_type} event from {instance}")
    logger.debug(data)
    if initiator.get("is_metagov_bot") == True:
        return
    try:
        slack_community = DiscordCommunity.objects.get(
            team_id=instance.community_platform_id, community__metagov_slug=instance.community.slug
        )
    except DiscordCommunity.DoesNotExist:
        logger.warn(f"No DiscordCommunity matches {instance}")
        return

    new_api_action = DiscordUtils.discord_event_to_action(slack_community, event_type, data, initiator)
    if new_api_action is not None:
        new_api_action.community_origin = True
        new_api_action.save()  # save triggers policy proposal
        logger.debug(f"Action saved: {new_api_action.pk}")


# @receiver(governance_process_updated, sender=DiscordVote)
# def discord_vote_updated_receiver(sender, instance, status, outcome, errors, **kwargs):
#     pass