import logging

import integrations.slack.utils as SlackUtils
from django.dispatch import receiver
from integrations.slack.models import SlackCommunity, SlackUser
from metagov.core.signals import governance_process_updated, platform_event_created
from metagov.plugins.slack.models import Slack, SlackEmojiVote
from policyengine.models import (
    BooleanVote,
    Proposal,
    ChoiceVote,
)

logger = logging.getLogger(__name__)

"""
Django signal handlers
"""


@receiver(platform_event_created, sender=Slack)
def slack_event_receiver(sender, instance, event_type, data, initiator, **kwargs):
    logger.debug("slack_event_reciever", extra={"slack_event_reciever.event_type": event_type, "slack_event_reciever.initiator": initiator, "slack_event_reciever.data": data})
    logger.debug(f"Received {event_type} event from {instance}")
    if initiator.get("is_metagov_bot") == True:
        logger.debug("slack_event_reciever: Ignoring event from Metagov bot")
        return
    try:
        slack_community = SlackCommunity.objects.get(
            team_id=instance.community_platform_id, community__metagov_slug=instance.community.slug
        )
    except SlackCommunity.DoesNotExist:
        logger.warning(f"slack_event_reciever: No SlackCommunity matches {instance}")
        return

    new_api_action = SlackUtils.slack_event_to_platform_action(slack_community, event_type, data, initiator)
    logger.debug("slack_event_reciever: got api action", extra={"slack_event_reciever.new_api_action": new_api_action})

    if new_api_action is not None:
        new_api_action.community_origin = True
        new_api_action.save()  # save triggers policy proposal
        logger.debug(f"GovernableAction saved: {new_api_action.pk}")


@receiver(governance_process_updated, sender=SlackEmojiVote)
def slack_vote_updated_receiver(sender, instance, status, outcome, errors, **kwargs):
    """
    Handle a change to an ongoing Metagov slack.emoji-vote GovernanceProcess.
    This function gets called any time a slack.emoji-vote gets updated (e.g. if a vote was cast).
    """

    try:
        proposal = Proposal.objects.get(governance_process=instance)
    except Proposal.DoesNotExist:
        # Proposal not saved yet, ignore
        return

    if proposal.status in [Proposal.PASSED, Proposal.FAILED]:
        logger.debug(f"Ignoring signal from {instance}, proposal {proposal.pk} has been completed")
        return

    logger.debug(f"Received vote update from {instance} - {instance.plugin.community_platform_id}")
    # logger.debug(outcome)

    try:
        slack_community = SlackCommunity.objects.get(
            team_id=instance.plugin.community_platform_id, community__metagov_slug=instance.plugin.community.slug
        )
    except SlackCommunity.DoesNotExist:
        logger.warn(f"No SlackCommunity matches {instance}")
        return

    votes = outcome["votes"]
    is_boolean_vote = set(votes.keys()) == {"yes", "no"}

    ### Count boolean vote
    if is_boolean_vote:
        for (vote_option, result) in votes.items():
            boolean_value = True if vote_option == "yes" else False
            for u in result["users"]:
                user, _ = SlackUser.objects.get_or_create(username=u, community=slack_community)
                existing_vote = BooleanVote.objects.filter(proposal=proposal, user=user).first()
                if existing_vote is None:
                    logger.debug(f"Counting boolean vote {boolean_value} by {user}")
                    BooleanVote.objects.create(proposal=proposal, user=user, boolean_value=boolean_value)
                elif existing_vote.boolean_value != boolean_value:
                    logger.debug(f"Counting boolean vote {boolean_value} by {user} (vote changed)")
                    existing_vote.boolean_value = boolean_value
                    existing_vote.save()
    ### Count choice vote
    else:
        for (vote_option, result) in votes.items():
            for u in result["users"]:
                user, _ = SlackUser.objects.get_or_create(username=u, community=slack_community)
                existing_vote = ChoiceVote.objects.filter(proposal=proposal, user=user).first()
                if existing_vote is None:
                    logger.debug(f"Counting vote for {vote_option} by {user} for proposal {proposal}")
                    ChoiceVote.objects.create(proposal=proposal, user=user, value=vote_option)
                elif existing_vote.value != vote_option:
                    logger.debug(f"Counting vote for {vote_option} by {user} for proposal {proposal} (vote changed)")
                    existing_vote.value = vote_option
                    existing_vote.save()

