import json
import logging

from django.contrib.auth.models import ContentType, Permission, User
from django.db import models
from policyengine.models import (Community, CommunityRole, CommunityUser,
                                 ConstitutionPolicy, PlatformAction,
                                 PlatformPolicy, Proposal, StarterKit)

logger = logging.getLogger(__name__)


class ExternalProcess(models.Model):
    location = models.CharField(max_length=100, blank=True)
    json_data = models.CharField(max_length=500, blank=True, null=True)
    policy = models.ForeignKey(PlatformPolicy, on_delete=models.CASCADE)
    action = models.ForeignKey(PlatformAction, on_delete=models.CASCADE)

    class Meta:
        unique_together = ["policy", "action"]


class MetagovUser(CommunityUser):
    provider = models.CharField(max_length=30, help_text="Identity provider that the username comes from")
    """
    Represents a user in the MetagovCommunity, which could be on any platform.
    """

    # Hack so it doesn't clash with usernames from other communities (django User requires unique username).
    # TODO(#299): make the CommunityUser model unique on community+username, not just username.
    def get_real_username(self):
        prefix = f"{self.provider}."
        if self.username.startswith(prefix):
            return self.username[len(prefix) :]
        return self.username


class MetagovPlatformAction(PlatformAction):
    """
    This is a PlatformAction model to use as a policy trigger for events received from Metagov.
    It does not represent a "governable" action, because `revert` and `execute` are not implemented (for now).
    Data about the event is stored as a json blob in the `json_data` field.
    """

    action_codename = "metagovaction"
    app_name = "metagov"
    json_data = models.CharField(max_length=500, blank=True, null=True)
    event_type = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return str(self.event_type)

    def get_metagov_action_data(self):
        if self.json_data:
            return json.loads(self.json_data)
        return None

    def execute(self):
        # because of https://github.com/amyxzhang/policykit/issues/305
        self.pass_action()

    def revert(self):
        pass
