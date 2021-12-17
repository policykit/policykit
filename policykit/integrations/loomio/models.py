import datetime
import logging

from django.db import models
from policyengine.metagov_app import metagov
from policyengine.models import CommunityPlatform, CommunityUser

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

        # Kick off process in Metagov
        mg_community = metagov.get_community(self.community.metagov_slug)
        plugin = mg_community.get_plugin("loomio")
        process = plugin.start_process(
            "poll",
            title=title,
            closing_at=closing_at,
            poll_type=poll_type,
            options=options,
            details=details or title,
            # pass on any other kwargs
            **kwargs,
        )
        proposal.governance_process = process
        proposal.save()
