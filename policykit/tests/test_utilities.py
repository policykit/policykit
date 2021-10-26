from django.test import TestCase
import policyengine.utils as Utils
from integrations.slack.models import SlackPostMessage
from constitution.models import PolicykitAddCommunityDoc
from integrations.opencollective.models import ExpenseApproved
import policyengine.autocomplete as PkAutocomplete

class UtilTests(TestCase):
    def test_find_cls(self):
        self.assertEqual(Utils.find_action_cls("slackpostmessage"), SlackPostMessage)
        self.assertEqual(Utils.find_action_cls("policykitaddcommunitydoc"), PolicykitAddCommunityDoc)
        self.assertTrue(PolicykitAddCommunityDoc in Utils.get_action_classes("constitution"))
        self.assertTrue(ExpenseApproved in Utils.get_trigger_classes("opencollective"))

    def test_autocomplete(self):
        self.assertTrue("action.channel" in PkAutocomplete.generate_action_autocompletes(SlackPostMessage))
