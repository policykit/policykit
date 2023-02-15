import logging

from django.db import models
from policyengine.models import CommunityPlatform

logger = logging.getLogger(__name__)


class SourcecredCommunity(CommunityPlatform):
    platform = "sourcecred"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def get_cred(self, username=None, id=None):
        result = self.metagov_plugin.get_cred(username=username, id=id)
        return result["value"]

    def fetch_total_credcred(self):
        result = self.metagov_plugin.fetch_total_cred()
        return result["value"]
