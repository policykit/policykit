import json
import logging

import requests
from django.db import models
from policyengine.models import CommunityUser, PlatformAction, BasePolicy

logger = logging.getLogger(__name__)


class MetagovProcessData(object):
    def __init__(self, obj):
        self.status = obj.get("status")
        self.errors = obj.get("errors")
        self.outcome = obj.get("outcome")


class MetagovProcess(models.Model):
    """
    Represents a governance process in Metagov. The governance process is tied to the unique
    "evaluation," or policy:action combination, that kicked it off using `start`.
    """

    location = models.CharField(max_length=100, blank=True)
    json_data = models.CharField(max_length=2000, blank=True, null=True)
    policy = models.ForeignKey(BasePolicy, on_delete=models.CASCADE)
    action = models.ForeignKey(PlatformAction, on_delete=models.CASCADE)

    class Meta:
        unique_together = ["policy", "action"]

    @property
    def data(self) -> MetagovProcessData:
        """
        A ``MetagovProcessData`` object with ``status`, ``errors``, and ``outcome``.
        This is the most recent data that we've received from Metagov at the Callback URL (post_outcome view).
        """
        if self.json_data:
            data = json.loads(self.json_data)
            return MetagovProcessData(data)
        return None

    def close(self):
        if self.data.status == "completed":
            # it's already closed, do nothing
            return

        logger.info(f"Making request to close process at '{self.location}'")
        response = requests.delete(self.location)
        if not response.ok:
            raise Exception(f"Error closing process: {response.status_code} {response.reason} {response.text}")
        logger.info(response.text)
        self.json_data = response.text
        self.save()


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


class MetagovPlatformAction(PlatformAction):
    """
    This is a PlatformAction model to use as a policy trigger for events received from Metagov.
    It does not represent a "governable" action, because `revert` and `execute` are not implemented (for now).
    Data about the event is stored as a json blob in the `json_data` field.
    """

    action_codename = "metagovaction"
    app_name = "metagov"
    json_data = models.CharField(max_length=2000, blank=True, null=True)
    event_type = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.event_type} ({self.pk})"

    @property
    def event_data(self):
        if self.json_data:
            return json.loads(self.json_data)
        return None

    def execute(self):
        pass

    def revert(self):
        pass
