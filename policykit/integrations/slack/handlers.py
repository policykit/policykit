import logging

import integrations.slack.utils as SlackUtils
from django.dispatch import receiver
from integrations.slack.models import SlackCommunity, SlackUser
from metagov.core.signals import governance_process_updated, platform_event_created
from metagov.plugins.slack.models import Slack, SlackEmojiVote
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


@receiver(platform_event_created, sender=Slack)
def slack_event_receiver(sender, instance, event_type, data, initiator, **kwargs):
    logger.debug(f"Received {event_type} event from {instance}")
    # logger.debug(data)
    if initiator.get("is_metagov_bot") == True:
        return
    try:
        slack_community = SlackCommunity.objects.get(
            team_id=instance.community_platform_id, community__metagov_slug=instance.community.slug
        )
    except SlackCommunity.DoesNotExist:
        logger.warn(f"No SlackCommunity matches {instance}")
        return

    new_api_action = SlackUtils.slack_event_to_platform_action(slack_community, event_type, data, initiator)
    if new_api_action is not None:
        new_api_action.community_origin = True
        new_api_action.is_bundled = False
        new_api_action.save()  # save triggers policy proposal
        logger.debug(f"GovernableAction saved: {new_api_action.pk}")


@receiver(governance_process_updated, sender=SlackEmojiVote)
def slack_vote_updated_receiver(sender, instance, status, outcome, errors, **kwargs):
    """
    Handle a change to an ongoing Metagov slack.emoji-vote GovernanceProcess.
    This function gets called any time a slack.emoji-vote associated with
    this SlackCommunity gets updated (e.g. if a vote was cast).
    """

    try:
        proposal = Proposal.objects.get(governance_process=instance)
    except Proposal.DoesNotExist:
        # Proposal not saved yet, ignore
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

    ### 1) Count boolean vote
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
    ### 2) Count number choice vote on action bundle
    elif proposal.action.action_type == "governableactionbundle":
        action_bundle = proposal.action
        # Expect this process to be a choice vote on an action bundle.
        bundled_actions = list(action_bundle.bundled_actions.all())
        for (k, v) in votes.items():
            num, voted_action = [(idx, a) for (idx, a) in enumerate(bundled_actions) if str(a) == k][0]

            try:
                proposal = Proposal.objects.get(action=voted_action)
            except Proposal.DoesNotExist:
                logger.warn(f"No policy proposal found action {voted_action} bundled in {action_bundle}. Ignoring")

            for u in v["users"]:
                user, _ = SlackUser.objects.get_or_create(username=u, community=slack_community)
                existing_vote = NumberVote.objects.filter(proposal=proposal, user=user).first()
                if existing_vote is None:
                    logger.debug(f"Counting number vote {num} by {user} for {voted_action} in bundle {action_bundle}")
                    NumberVote.objects.create(proposal=proposal, user=user, number_value=num)
                elif existing_vote.number_value != num:
                    logger.debug(
                        f"Counting number vote {num} by {user} for {voted_action} in bundle {action_bundle} (vote changed)"
                    )
                    existing_vote.number_value = num
                    existing_vote.save()
    ### 2) Count choice vote
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
