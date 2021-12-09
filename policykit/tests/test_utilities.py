from django.test import TestCase
import policyengine.utils as Utils
from policyengine.models import PolicyActionKind
from integrations.slack.models import SlackPostMessage
from constitution.models import PolicykitAddCommunityDoc
from integrations.opencollective.models import ExpenseApproved
import policyengine.autocomplete as PkAutocomplete
import policyengine.tests.utils as TestUtils


class UtilTests(TestCase):
    def test_find_cls(self):
        self.assertEqual(Utils.find_action_cls("slackpostmessage"), SlackPostMessage)
        self.assertEqual(Utils.find_action_cls("policykitaddcommunitydoc"), PolicykitAddCommunityDoc)
        self.assertTrue(PolicykitAddCommunityDoc in Utils.get_action_classes("constitution"))
        self.assertTrue(ExpenseApproved in Utils.get_trigger_classes("opencollective"))

    def test_autocomplete(self):
        self.assertTrue("action.channel" in PkAutocomplete.generate_action_autocompletes(SlackPostMessage))

    def test_action_type_util(self):
        slack_community, user = TestUtils.create_slack_community_and_user()
        community = slack_community.community

        actions = Utils.get_action_types(community, [PolicyActionKind.CONSTITUTION])
        self.assertIsNotNone(actions["constitution"])
        actions = Utils.get_action_types(community, [PolicyActionKind.PLATFORM])

        self.assertIsNotNone(actions["slack"])

        actions = Utils.get_action_types(community, [PolicyActionKind.TRIGGER])
        self.assertIsNotNone(actions["any platform"])