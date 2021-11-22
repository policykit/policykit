import logging

from django.db import models
from policyengine.metagov_app import metagov
from policyengine.models import CommunityPlatform, CommunityUser, TriggerAction

logger = logging.getLogger(__name__)


class OpencollectiveUser(CommunityUser):
    pass


class OpencollectiveCommunity(CommunityPlatform):
    platform = "opencollective"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def post_message(self, text, expense_id):
        mg_community = metagov.get_community(self.community.metagov_slug)
        return mg_community.perform_action(
            plugin_name="opencollective",
            action_id="create-comment",
            parameters={"raw": text, "expense_id": expense_id},
            jsonschema_validation=True,
            community_platform_id=self.team_id,
        )

    def process_expense(self, expense_id, action):
        mg_community = metagov.get_community(self.community.metagov_slug)
        return mg_community.perform_action(
            plugin_name="opencollective",
            action_id="process-expense",
            parameters={"expense_id": expense_id, "action": action},
            jsonschema_validation=True,
            community_platform_id=self.team_id,
        )


class ExpenseEvent(TriggerAction):
    data = models.JSONField()

    class Meta:
        abstract = True

    @property
    def expense_id(self):
        return self.data.get("id")

    @property
    def url(self):
        return self.data.get("url")

    @property
    def description(self):
        return self.data.get("description")


class ExpenseCreated(ExpenseEvent):
    pass


class ExpenseRejected(ExpenseEvent):
    pass


class ExpenseApproved(ExpenseEvent):
    pass


class ExpenseDeleted(ExpenseEvent):
    pass


class ExpenseUnapproved(ExpenseEvent):
    pass


class ExpensePaid(ExpenseEvent):
    pass
