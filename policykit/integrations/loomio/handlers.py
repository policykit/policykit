import logging

from django.dispatch import receiver
from integrations.loomio.models import LoomioCommunity, LoomioUser
from metagov.core.signals import governance_process_updated
from metagov.plugins.loomio.models import LoomioPoll
from policyengine.models import ChoiceVote, Proposal

logger = logging.getLogger(__name__)


@receiver(governance_process_updated, sender=LoomioPoll)
def loomio_vote_updated_receiver(sender, instance, status, outcome, errors, **kwargs):
    """
    Handle a change to an ongoing Loomio poll GovernanceProcess.
    This function gets called any time a poll associated with
    this LoomioCommunity gets updated (e.g. if a vote was cast).
    """
    try:
        proposal = Proposal.objects.get(governance_process=instance)
    except Proposal.DoesNotExist:
        # Proposal not saved yet, ignore
        return

    logger.debug(f"Received vote update from {instance} - {instance.plugin.community_platform_id}")
    # logger.debug(outcome)

    try:
        loomio_community = LoomioCommunity.objects.get(
            team_id=instance.plugin.community_platform_id, community__metagov_slug=instance.plugin.community.slug
        )
    except LoomioCommunity.DoesNotExist:
        logger.warn(f"No LoomioCommunity matches {instance}")
        return

    votes = outcome["votes"]

    for (vote_option, result) in votes.items():
        for u in result["users"]:
            user, _ = LoomioUser.objects.get_or_create(username=u, readable_name=u, community=loomio_community)
            existing_vote = ChoiceVote.objects.filter(proposal=proposal, user=user).first()
            if existing_vote is None:
                logger.debug(f"Casting vote for {vote_option} by {user} for proposal {proposal}")
                ChoiceVote.objects.create(proposal=proposal, user=user, value=vote_option)
            elif existing_vote.value != vote_option:
                logger.debug(f"Casting vote for {vote_option} by {user} for proposal {proposal} (vote changed)")
                existing_vote.value = vote_option
                existing_vote.save()
