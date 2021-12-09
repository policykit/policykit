import logging

from django.dispatch import receiver
from integrations.github.models import GithubCommunity, GithubUser
from metagov.core.signals import governance_process_updated, platform_event_created
from metagov.plugins.github.models import Github, GithubIssueReactVote
from policyengine.models import BooleanVote, Proposal

logger = logging.getLogger(__name__)


@receiver(platform_event_created, sender=Github)
def github_event_receiver(sender, instance, event_type, data, initiator, **kwargs):
    logger.debug(f"Received {event_type} event from {instance}")


@receiver(governance_process_updated, sender=GithubIssueReactVote)
def github_vote_updated_receiver(sender, instance, status, outcome, errors, **kwargs):
    """
    Handle a change to an ongoing Metagov slack.emoji-vote GovernanceProcess.
    This function gets called any time a slack.emoji-vote associated with
    this GithubCommunity gets updated (e.g. if a vote was cast).
    """

    try:
        proposal = Proposal.objects.get(governance_process=instance)
    except Proposal.DoesNotExist:
        # Proposal not saved yet, ignore
        return

    logger.debug(f"Received vote update from {instance} - {instance.plugin.community_platform_id}")
    # logger.debug(outcome)

    try:
        github_community = GithubCommunity.objects.get(
            team_id=instance.plugin.community_platform_id, community__metagov_slug=instance.plugin.community.slug
        )
    except GithubCommunity.DoesNotExist:
        logger.warn(f"No GithubCommunity matches {instance}")
        return

    votes = outcome["votes"]

    # Expect this process to be a boolean vote
    for (k, v) in votes.items():
        assert k == "yes" or k == "no"
        reaction_bool = True if k == "yes" else False
        for u in v["users"]:
            user, _ = GithubUser.objects.get_or_create(username=u, readable_name=u, community=github_community)
            existing_vote = BooleanVote.objects.filter(proposal=proposal, user=user).first()
            if existing_vote is None:
                logger.debug(f"Casting boolean vote {reaction_bool} by {user} for {proposal.action}")
                BooleanVote.objects.create(proposal=proposal, user=user, boolean_value=reaction_bool)
            elif existing_vote.boolean_value != reaction_bool:
                logger.debug(f"Casting boolean vote {reaction_bool} by {user} for {proposal.action} (vote changed)")
                existing_vote.boolean_value = reaction_bool
                existing_vote.save()
