import json
import logging

from django.db import models
from policyengine.models import CommunityUser, TriggerAction
import integrations.metagov.api as MetagovAPI

logger = logging.getLogger(__name__)


class MetagovUser(CommunityUser):
    """
    Represents a user in the Metagov community, which could be on any platform.
    """

    provider = models.CharField(max_length=30, help_text="Identity provider that the username comes from")

    # Hack so it doesn't clash with usernames from other communities (django User requires unique username).
    # TODO(#299): make the CommunityUser model unique on community+username, not just username.
    @property
    def external_username(self):
        prefix = f"{self.provider}."
        if self.username.startswith(prefix):
            return self.username[len(prefix) :]
        return self.username

    # def get_metagov_id(self):
    #     return MetagovAPI.find_metagov_id(
    #         community=self.community.community.metagov_slug,
    #         platform_type=self.provider,
    #         #community_platform_id=self.community.team_id,
    #         platform_identifier=self.external_username  
    #     )

class MetagovConfig(models.Model):
    """
    Dummy model for permissions to edit Metagov Config.
    """

    class Meta:
        # No database table creation or deletion  \
        # operations will be performed for this model.
        managed = False

        # disable "add", "change", "delete"
        # and "view" default permissions
        default_permissions = ()

        permissions = [("can_edit_metagov_config", "Can edit Metagov config")]


class MetagovTrigger(TriggerAction):
    """
    This model represents a trigger event received from Metagov.
    Data about the event is stored as a json blob in the `json_data` field.
    """

    json_data = models.JSONField(blank=True, null=True)
    event_type = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"Metagov Event: {self.event_type}"

    @property
    def event_data(self):
        if self.json_data:
            return json.loads(self.json_data)
        return None
