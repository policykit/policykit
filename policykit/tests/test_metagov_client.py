import os
import unittest

from django.test import Client, TestCase
from django_db_logger.models import EvaluationLog
from integrations.slack.models import SlackPinMessage
from policyengine.metagov_app import metagov
from policyengine.metagov_client import Metagov
from policyengine.models import ActionType, Policy, Proposal, WebhookTriggerAction
from policyengine.tasks import consider_proposed_actions

import tests.utils as TestUtils


class MetagovTests(TestCase):
    def setUp(self):
        # Set up a Slack community and a user
        self.slack_community, self.user = TestUtils.create_slack_community_and_user()
        self.community = self.slack_community.community

        # Enable a plugin to use in tests
        self.metagov_community = metagov.get_community(self.community.metagov_slug)
        self.metagov_community.enable_plugin("randomness", {"default_low": 2, "default_high": 200})

    def tearDown(self):
        self.community.delete()

    def test_close_process(self):
        """Integration-test metagov process with randomness plugin. Process is closed from within the policy."""
        # 1) Create Policy and GovernableAction
        policy_code = {
            **TestUtils.ALL_ACTIONS_PASS,
            "initialize": """
metagov.start_process("randomness.delayed-stochastic-vote", options=["one", "two", "three"], delay=1)
""",
            "check": """
result = metagov.close_process()
proposal.data.set('reached_close', True)

if result is None:
    return #still processing
if result.errors:
    return FAILED
if result.outcome:
    return PASSED if result.outcome.get('winner') else FAILED
return FAILED
""",
        }
        policy = Policy(
            **policy_code,
            kind=Policy.PLATFORM,
            community=self.community,
        )
        policy.save()

        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.slack_community
        action.community_origin = True

        # 2) Save action to trigger policy execution
        action.save()

        proposal = Proposal.objects.get(action=action, policy=policy)
        self.assertEqual(proposal.status, Proposal.PASSED)
        self.assertTrue(proposal.is_vote_closed)
        self.assertEqual(proposal.data.get("reached_close"), True)

        # assert that the process outcome was saved
        metagov = Metagov(proposal)
        process_data = metagov.get_process()
        self.assertEqual(process_data.status, "completed")
        self.assertIsNotNone(process_data.outcome.get("winner"))

    def test_outcome_endpoint(self):
        """Integration-test metagov process is updated via the outcome receiver endpoint in PolicyKit"""
        # 1) Create Policy and GovernableAction
        policy_code = {
            **TestUtils.ALL_ACTIONS_PASS,
            "initialize": """
metagov.start_process("randomness.delayed-stochastic-vote", options=["one", "two", "three"], delay=1)
""",
            "check": """
result = metagov.get_process()
proposal.data.set('process_status', result.status)
proposal.data.set('is_vote_closed', proposal.is_vote_closed)

if result is None or result.status == "pending":
    return None #still processing
if result.errors:
    return FAILED
if result.outcome:
    return PASSED if result.outcome.get('winner') else FAILED
return FAILED
""",
        }
        policy = Policy(
            **policy_code,
            kind=Policy.PLATFORM,
            community=self.community,
        )
        policy.save()

        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.slack_community
        action.community_origin = True
        action.revert = lambda: None
        action.execute = lambda: None

        # 2) Save action to trigger policy execution
        action.save()

        proposal = Proposal.objects.get(action=action, policy=policy)
        self.assertEqual(proposal.status, Proposal.PROPOSED)
        self.assertEqual(proposal.data.get("process_status"), "pending")
        self.assertFalse(proposal.data.get("is_vote_closed"))
        self.assertFalse(proposal.is_vote_closed)

        # 2) Close the process, which should emit a signal for PolicyKit to handle
        proposal.governance_process.update()
        proposal.governance_process.proxy.close()

        # re-run proposal using celery task function
        consider_proposed_actions()
        proposal.refresh_from_db()

        self.assertEqual(proposal.status, Proposal.PASSED)

        metagov = Metagov(proposal)
        process_data = metagov.get_process()
        self.assertEqual(process_data.status, "completed")
        self.assertIsNotNone(process_data.outcome.get("winner"))

    def test_perform_action(self):
        """Integration-test metagov.perform_action function with randomness plugin"""
        # 1) Create Policy that performs a metagov action
        policy = Policy(kind=Policy.PLATFORM)
        policy.community = self.community
        policy.filter = "return True"
        policy.initialize = "logger.debug('help!')"
        policy.check = """
response = metagov.perform_action('randomness.random-int', low=4, high=5)
if response and response.get('value') == 4:
    return PASSED
return FAILED"""
        policy.notify = "pass"
        policy.success = "pass"
        policy.fail = "pass"
        policy.description = "test"
        policy.name = "test policy"
        policy.save()

        # 2) Save an action to trigger the policy execution
        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.slack_community
        action.community_origin = True
        action.revert = lambda: None
        action.execute = lambda: None
        action.save()

        proposal = Proposal.objects.get(action=action, policy=policy)
        self.assertEqual(proposal.status, Proposal.PASSED)

        # Check that proposal debug log was generated
        from django_db_logger.models import EvaluationLog

        self.assertEqual(EvaluationLog.objects.filter(proposal=proposal, msg__contains="help!").count(), 1)


@unittest.skipUnless("INTEGRATION" in os.environ, "Skipping Metagov integration tests")
class WebhookTriggerActionTest(TestCase):
    def setUp(self):
        self.slack_community, self.user = TestUtils.create_slack_community_and_user()
        self.community = self.slack_community.community

    def tearDown(self):
        self.community.delete()

    def test_metagov_trigger(self):
        """Test policy triggered by generic metagov event"""
        # 1) Create Policy that is triggered by a metagov action

        policy = Policy(kind=Policy.TRIGGER)
        policy.community = self.community
        policy.filter = """return action.event_type == 'discourse.post_created'"""
        policy.initialize = "pass"
        policy.notify = "pass"
        policy.check = "return PASSED if action.event_data['category'] == 0 else FAILED"
        policy.success = "pass"
        policy.fail = "pass"
        policy.description = "test"
        policy.name = "test policy"
        policy.save()
        policy.action_types.add(ActionType.objects.create(codename="WebhookTriggerAction"))

        event_payload = {
            "community": self.community.metagov_slug,
            "initiator": {"user_id": "miriam", "provider": "discourse"},
            "source": "discourse",
            "event_type": "post_created",
            "data": {"title": "test", "raw": "post text", "category": 0},
        }

        # 2) Mimick an incoming notification from Metagov that the action has occurred
        client = Client()
        response = client.post(f"/metagov/internal/action", data=event_payload, content_type="application/json")

        self.assertEqual(response.status_code, 200)

        self.assertEqual(WebhookTriggerAction.objects.all().count(), 1)

        action = WebhookTriggerAction.objects.filter(event_type="discourse.post_created").first()

        # the action.community is the community that is connected to metagov
        self.assertEqual(action.action_type, "WebhookTriggerAction")
        self.assertEqual(action.community.platform, "slack")
        self.assertEqual(action.data["raw"], "post text")

        proposal = Proposal.objects.get(action=action, policy=policy)
        self.assertEqual(proposal.data.get("test_verify_username"), "miriam")
        self.assertEqual(proposal.status, Proposal.PASSED)

    def test_metagov_slack_trigger(self):
        """Test receiving a Slack event from Metagov that creates a SlackPinMessage action"""
        # 1) Create Policy that is triggered by a metagov action
        policy = Policy(kind=Policy.PLATFORM)
        policy.community = self.community
        policy.filter = """return action.action_type == 'slackpinmessage'"""
        policy.initialize = "pass"
        policy.notify = "pass"
        policy.check = "return PASSED"
        policy.success = "proposal.data.set('got here', True)\nlogger.debug('hello world!')"
        policy.fail = "pass"
        policy.description = "test"
        policy.name = "test policy"
        policy.save()

        event_payload = {
            "community": self.slack_community.metagov_slug,
            "initiator": {"user_id": "alice", "provider": "slack"},
            "source": "slack",
            "event_type": "pin_added",
            "data": {"channel_id": "123", "item": {"message": {"ts": "123"}}},
        }

        # 2) Mimick an incoming notification from Metagov that the action has occurred
        client = Client()
        response = client.post(f"/metagov/internal/action", data=event_payload, content_type="application/json")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SlackPinMessage.objects.all().count(), 1)

        action = SlackPinMessage.objects.first()
        self.assertEqual(action.community.platform, "slack")

        proposal = Proposal.objects.get(action=action, policy=policy)
        self.assertEqual(proposal.data.get("got here"), True)
        self.assertEqual(proposal.status, Proposal.PASSED)

        # Check that proposal debug log was generated
        self.assertEqual(EvaluationLog.objects.filter(proposal=proposal, msg__contains="hello world!").count(), 1)
