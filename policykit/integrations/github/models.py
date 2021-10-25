import logging

from django.conf import settings
from django.db import models
from policyengine.utils import default_boolean_vote_message
from policyengine.models import (
    BooleanVote,
    CommunityPlatform,
    CommunityUser,
)
from integrations.metagov.library import Metagov

logger = logging.getLogger(__name__)


class GithubUser(CommunityUser):
    pass


class GithubCommunity(CommunityPlatform):
    platform = "github"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def initiate_vote(self, proposal, repo_name, template=None):
        payload = {
            "callback_url": f"{settings.SERVER_URL}/metagov/internal/outcome/{proposal.pk}",
            "repo_name": repo_name,
            "question": template or default_boolean_vote_message(proposal.policy),
        }
        # Kick off process in Metagov
        metagov = Metagov(proposal)
        process = metagov.start_process("github.issue-react-vote", payload)

        # Save the issue number as "community post" so policy author can access it?
        proposal.community_post = process.outcome["issue_number"]
        proposal.save()

    def _handle_metagov_process(self, proposal, process):
        """
        Handle a change to an ongoing Metagov github vote GovernanceProcess.
        This function gets called any time a github vote associated with
        this GithubCommunity gets updated (e.g. if a vote was cast).
        """
        outcome = process["outcome"]
        votes = outcome["votes"]
        action = proposal.action

        # Expect this process to be a boolean vote on an action.
        for (k, v) in votes.items():
            assert k == "yes" or k == "no"
            reaction_bool = True if k == "yes" else False
            for u in v["users"]:
                user, _ = GithubUser.objects.get_or_create(username=u, readable_name=u, community=self)
                existing_vote = BooleanVote.objects.filter(proposal=proposal, user=user).first()
                if existing_vote is None:
                    logger.debug(f"Casting boolean vote {reaction_bool} by {user} for {action}")
                    BooleanVote.objects.create(proposal=proposal, user=user, boolean_value=reaction_bool)
                elif existing_vote.boolean_value != reaction_bool:
                    logger.debug(f"Casting boolean vote {reaction_bool} by {user} for {action} (vote changed)")
                    existing_vote.boolean_value = reaction_bool
                    existing_vote.save()

    def _handle_metagov_event(self, outer_event):
        """
        Receive Github Metagov Event for this community
        """
        logger.debug(f"GithubCommunity recieved metagov event: {outer_event['event_type']}")
        if outer_event["initiator"].get("is_metagov_bot") == True:
            logger.debug("Ignoring bot event")
            return