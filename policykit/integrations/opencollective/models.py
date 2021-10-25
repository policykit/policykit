import logging
import json
from django.db import models
from policyengine.models import (
    TriggerAction,
    CommunityPlatform,
    CommunityUser,
)
import integrations.metagov.api as MetagovAPI

logger = logging.getLogger(__name__)


class OpencollectiveUser(CommunityUser):
    pass


class OpencollectiveCommunity(CommunityPlatform):
    platform = "opencollective"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def _handle_metagov_event(self, outer_event):
        """
        Receive Opencollective Metagov Event for this community
        """
        logger.debug(f"OpencollectiveCommunity recieved metagov event: {outer_event['event_type']}")
        if outer_event["initiator"].get("is_metagov_bot") == True:
            return None

        event_type = outer_event["event_type"]
        event_data = json.dumps(outer_event["data"])

        trigger_action = None

        if event_type == "expense_created":
            trigger_action = ExpenseCreated(json_data=event_data)
        elif event_type == "expense_rejected":
            trigger_action = ExpenseRejected(json_data=event_data)
        elif event_type == "expense_approved":
            trigger_action = ExpenseApproved(json_data=event_data)
        elif event_type == "expense_deleted":
            trigger_action = ExpenseDeleted(json_data=event_data)
        elif event_type == "expense_unapproved":
            trigger_action = ExpenseUnapproved(json_data=event_data)
        elif event_type == "expense_paid":
            trigger_action = ExpensePaid(json_data=event_data)

        if not trigger_action:
            return None

        trigger_action.community = self

        # Get or create the Open Collective user that initiated the trigger
        oc_username = outer_event.get("initiator", {}).get("user_id")
        if oc_username:
            user, _ = OpencollectiveUser.objects.get_or_create(
                username=oc_username,
                readable_name=oc_username,
                community=self,
            )
            trigger_action.initiator = user

        trigger_action.evaluate()
        return trigger_action

    def post_message(self, text, expense_id):
        return MetagovAPI.perform_action(
            community_slug=self.community.metagov_slug,
            name="opencollective.create-comment",
            parameters={"expense_id": expense_id, "raw": text},
        )

    def process_expense(self, expense_id, action):
        return MetagovAPI.perform_action(
            community_slug=self.community.metagov_slug,
            name="opencollective.process-expense",
            parameters={"expense_id": expense_id, "action": action},
        )


class ExpenseEvent(TriggerAction):
    json_data = models.JSONField()

    class Meta:
        abstract = True

    @property
    def raw_data(self):
        if self.json_data:
            return json.loads(self.json_data)
        return None

    def _get_data_field(self, field):
        data = self.raw_data
        if data:
            return data.get(field)
        return None

    @property
    def expense_id(self):
        return self._get_data_field("id")

    @property
    def url(self):
        return self._get_data_field("url")

    @property
    def description(self):
        return self._get_data_field("description")


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
