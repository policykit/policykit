import logging

from django.db import models
from policyengine.metagov_app import metagov
from policyengine.models import CommunityPlatform, CommunityUser, TriggerAction, BaseAction

logger = logging.getLogger(__name__)


class OpencollectiveUser(CommunityUser):
    pass


class OpencollectiveCommunity(CommunityPlatform):
    platform = "opencollective"

    team_id = models.CharField("team_id", max_length=150, unique=True)

    def post_message(self, proposal, text, expense_id):

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

class OpenCollectivePostMessage(BaseAction):
    EXECUTE_PARAMETERS = ["text", "expense_id"]
    EXECUTE_VARIABLES = [
        {
            "name": "text",
            "label": "Message to be posted",
            "entity": None,
            "default_value": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "expense_id",
            "label": "ID of the expense we will post message under",
            "entity": "",
            "default_value": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        }
    ]

    text = models.TextField()
    expense_id = models.CharField("expense_id", max_length=150)

    class Meta:
        permissions = (("can_execute_opencollectivepostmessage", "Can execute open collective post message"),)

    
    def execution_codes(**kwargs):
        text = kwargs.get("text", "")
        expense_id = kwargs.get("expense_id", "")
        return f"opencollective.post_message(text={text}, expense_id={expense_id})"

class OpenCollectiveProcessExpense(BaseAction):
    EXECUTE_PARAMETERS = ["expense_id", "action"]
    EXECUTE_VARIABLES = [
        {
            "name": "expense_id",
            "label": "ID of the expense we will process",
            "entity": None,
            "default_value": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "process_action",
            "label": "Action to be taken on the expense",
            "entity": "",
            "default_value": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        }
    ]

    expense_id = models.CharField("expense_id", max_length=150)
    action = models.CharField("action", max_length=150)

    class Meta:
        permissions = (("can_execute_opencollectiveprocessexpense", "Can execute open collective process expense"),)

    def execution_codes(**kwargs):
        expense_id = kwargs.get("expense_id", "")
        action = kwargs.get("process_action", "")
        return f"opencollective.process_expense(action={action}, expense_id={expense_id})"

class ExpenseEvent(TriggerAction):
    data = models.JSONField()
    FILTER_PARAMETERS = {
        "description": "OpencollectiveExpenseContent", "type": "OpencollectiveExpenseType",
        "amount": "OpencollectiveAmount", 
        "tags": "OpencollectiveExpenseTag" #TODO
    }
    
    class Meta:
        abstract = True

    @property
    def expense_id(self):
        return self.data.get("id")
    
    @property
    def type(self):
        return self.data.get("type")
    
    @property
    def amount(self):
        return self.data.get("amount")
    
    @property
    def formatted_amount(self):
        return '${:,.2f}'.format(self.amount / 100)

    @property
    def currency(self):
        return self.data.get('currency')
    
    @property
    def tags(self):
        return self.data.get("tags")

    @property
    def url(self):
        return self.data.get("url")

    @property
    def description(self):
        return self.data.get("description")

    @property
    def expense_user_slug(self):
        return self.data.get('payee').get('slug')


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
