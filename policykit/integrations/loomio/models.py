import logging
from django.db import models
from policyengine.models import (
    ChoiceVote,
    CommunityPlatform,
    CommunityUser,
)
from integrations.metagov.library import Metagov
import datetime
from django.conf import settings

logger = logging.getLogger(__name__)


class LoomioUser(CommunityUser):
    pass


class LoomioCommunity(CommunityPlatform):
    platform = "loomio"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def initiate_vote(self, proposal, title, closing_at, options, details=None, poll_type="proposal", **kwargs):
        """
        Start a new poll on Loomio.

        Accepted keyword args:
            subgroup,
            specified_voters_only,
            hide_results_until_closed,
            anonymous,
            discussion_id,
            voter_can_add_options,
            recipient_audience,
            notify_on_closing_soon,
            recipient_user_ids,
            recipient_emails,
            recipient_message
        """

        if isinstance(closing_at, datetime.datetime):
            closing_at = closing_at.strftime("%Y-%m-%d")

        payload = {
            "title": title,
            "closing_at": closing_at,
            "poll_type": poll_type,
            "options": options,
            "details": details,
            "callback_url": f"{settings.SERVER_URL}/metagov/internal/outcome/{proposal.pk}",
            **kwargs,
        }

        # Kick off process in Metagov
        metagov = Metagov(proposal)
        process = metagov.start_process("loomio.poll", payload)
        proposal.community_post = process.outcome["poll_url"]
        logger.debug(
            f"Saving proposal with community_post '{proposal.community_post}', and process at {proposal.governance_process_url}"
        )
        proposal.save()

    def _handle_metagov_event(self, proposal, process):
        """
        Handle a change to an ongoing Loomio poll GovernanceProcess.
        Creates or updates ChoiceVote records.
        """
        logger.debug(f"received loomio vote update: {str(process)}")
        outcome = process["outcome"]
        votes = outcome["votes"]

        for (vote_option, result) in votes.items():
            for u in result["users"]:
                user, _ = LoomioUser.objects.get_or_create(username=u, readable_name=u, community=self)
                existing_vote = ChoiceVote.objects.filter(proposal=proposal, user=user).first()
                if existing_vote is None:
                    logger.debug(f"Casting vote for {vote_option} by {user} for proposal {proposal}")
                    ChoiceVote.objects.create(proposal=proposal, user=user, value=vote_option)
                elif existing_vote.value != vote_option:
                    logger.debug(f"Casting vote for {vote_option} by {user} for proposal {proposal} (vote changed)")
                    existing_vote.value = vote_option
                    existing_vote.save()
