import logging

from django.db import models
from policyengine.models import CommunityPlatform, CommunityUser
from policyengine.utils import default_boolean_vote_message

logger = logging.getLogger(__name__)


class GithubUser(CommunityUser):
    pass


class GithubCommunity(CommunityPlatform):
    platform = "github"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def initiate_vote(self, proposal, repo_name, template=None):
        question = template or default_boolean_vote_message(proposal.policy)

        # Kick off process in Metagov
        process = self.metagov_plugin.start_process("issue-react-vote", repo_name=repo_name, question=question)

        # Save the issue number as "community post" so policy author can access it?
        proposal.governance_process = process
        proposal.community_post = process.outcome["issue_number"]
        proposal.save()
