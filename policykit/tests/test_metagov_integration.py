"""
Tests that require Metagov to be running.
Run with `INTEGRATION=1 python manage.py test`
"""
import os
import unittest

import integrations.metagov.api as MetagovAPI
from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import Client, LiveServerTestCase, TestCase
from django_db_logger.models import EvaluationLog
from integrations.metagov.models import MetagovAction
from integrations.metagov.library import Metagov
from integrations.slack.models import SlackCommunity, SlackPinMessage, SlackUser
from policyengine.models import Community, CommunityRole, Policy, PolicyEvaluation
from policyengine import engine

all_actions_pass_policy = {
    "filter": "return True",
    "initialize": "pass",
    "notify": "pass",
    "check": "return PASSED",
    "success": "pass",
    "fail": "pass",
}


@unittest.skipUnless("INTEGRATION" in os.environ, "Skipping Metagov integration tests")
class IntegrationTests(LiveServerTestCase):
    def setUp(self):
        # Set SERVER_URL to live server so that Metagov can hit PolicyKit outcome receiver endpoint
        settings.SERVER_URL = self.live_server_url
        print(f"Setting up integration tests: PolicyKit @ {settings.SERVER_URL}, Metagov @ {settings.METAGOV_URL}")

        # Set up a Slack community and a user
        user_group = CommunityRole.objects.create(role_name="fake role", name="testing role")
        can_add = Permission.objects.get(name="Can add slack pin message")
        user_group.permissions.add(can_add)
        self.community = Community.objects.create()
        self.slack_community = SlackCommunity.objects.create(
            community_name="my test community",
            community=self.community,
            team_id="TMQ3PKX",
            base_role=user_group,
        )
        self.user = SlackUser.objects.create(username="test", community=self.slack_community)

        # Activate a plugin to use in tests
        MetagovAPI.update_metagov_community(
            community=self.slack_community,
            plugins=list([{"name": "randomness", "config": {"default_low": 2, "default_high": 200}}]),
        )

    def tearDown(self):
        # Delete parent community to trigger deletion of Metagov Community
        self.community.delete()

    def test_close_process(self):
        """Integration-test metagov process with randomness plugin. Process is closed from within the policy."""
        # 1) Create Policy and PlatformAction
        policy_code = {
            **all_actions_pass_policy,
            "initialize": """
metagov.start_process("randomness.delayed-stochastic-vote", {"options": ["one", "two", "three"], "delay": 1})
""",
            "check": """
result = metagov.close_process()
evaluation.data.set('reached_close', True)

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
            community=self.slack_community,
            description="test",
            name="test policy",
        )
        policy.save()

        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.slack_community
        action.community_origin = True

        # 2) Save action to trigger policy execution
        action.save()

        evaluation = PolicyEvaluation.objects.get(action=action, policy=policy)
        self.assertEqual(evaluation.status, PolicyEvaluation.PASSED)
        self.assertEqual(evaluation.data.get("reached_close"), True)

        # assert that the process outcome was saved
        metagov = Metagov(evaluation)
        process_data = metagov.get_process()
        self.assertEqual(process_data.status, "completed")
        self.assertIsNotNone(process_data.outcome.get("winner"))

    def test_outcome_endpoint(self):
        """Integration-test metagov process is updated via the outcome receiver endpoint in PolicyKit"""
        # 1) Create Policy and PlatformAction
        policy_code = {
            **all_actions_pass_policy,
            "initialize": """
metagov.start_process("randomness.delayed-stochastic-vote", {"options": ["one", "two", "three"], "delay": 1})
""",
            "check": """
result = metagov.get_process()
evaluation.data.set('process_status', result.status)

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
            community=self.slack_community,
            description="test",
            name="test policy",
        )
        policy.save()

        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.slack_community
        action.community_origin = True
        action.revert = lambda: None # unset revert function so we don't try to hit slack

        # 2) Save action to trigger policy execution
        action.save()

        evaluation = PolicyEvaluation.objects.get(action=action, policy=policy)
        self.assertEqual(evaluation.status, PolicyEvaluation.PROPOSED)
        self.assertEqual(evaluation.data.get("process_status"), "pending")

        # 2) Mimick an incoming notification from Metagov that the process has updated
        payload = {
            "name": "randomness.delayed-stochastic-vote",
            "community": self.slack_community.metagov_slug,
            "status": "completed",
            "outcome": {"winner": "three"},
        }

        client = Client()
        response = client.post(
            f"/metagov/internal/outcome/{evaluation.pk}", data=payload, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        evaluation.refresh_from_db()  # refresh because the outcome data should have been updated

        # re-run evaluation
        engine.run_evaluation(evaluation)

        self.assertEqual(evaluation.status, PolicyEvaluation.PASSED)

        metagov = Metagov(evaluation)
        process_data = metagov.get_process()
        self.assertEqual(process_data.status, "completed")
        self.assertIsNotNone(process_data.outcome.get("winner"))

    def test_perform_action(self):
        """Integration-test metagov.perform_action function with randomness plugin"""
        # 1) Create Policy that performs a metagov action
        policy = Policy(kind=Policy.PLATFORM)
        policy.community = self.slack_community
        policy.filter = "return True"
        policy.initialize = "debug('help!')"
        policy.check = """parameters = {"low": 4, "high": 5}
response = metagov.perform_action('randomness.random-int', parameters)
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
        action.save()

        evaluation = PolicyEvaluation.objects.get(action=action, policy=policy)
        self.assertEqual(evaluation.status, PolicyEvaluation.PASSED)

        # Check that evaluation debug log was generated
        from django_db_logger.models import EvaluationLog

        self.assertEqual(EvaluationLog.objects.filter(evaluation=evaluation, msg__contains="help!").count(), 1)


@unittest.skipUnless("INTEGRATION" in os.environ, "Skipping Metagov integration tests")
class MetagovActionTest(TestCase):
    def setUp(self):
        user_group = CommunityRole.objects.create(role_name="fake role 2", name="testing role 2")
        p1 = Permission.objects.get(name="Can add slack pin message")
        user_group.permissions.add(p1)
        self.community = Community.objects.create()
        self.slack_community = SlackCommunity.objects.create(
            community_name="test community",
            community=self.community,
            team_id="test000",
            base_role=user_group,
        )

    def tearDown(self):
        # Delete parent community to trigger deletion of Metagov Community
        self.community.delete()

    def test_metagov_trigger(self):
        """Test policy triggered by generic metagov event"""
        # 1) Create Policy that is triggered by a metagov action

        policy = Policy(kind=Policy.PLATFORM)
        policy.community = self.slack_community
        policy.filter = """return action.action_type == 'metagovaction' \
and action.event_type == 'discourse.post_created'"""
        policy.initialize = (
            "evaluation.data.set('test_verify_username', action.initiator.metagovuser.external_username)"
        )
        policy.notify = "pass"
        policy.check = "return PASSED if action.event_data['category'] == 0 else FAILED"
        policy.success = "pass"
        policy.fail = "pass"
        policy.description = "test"
        policy.name = "test policy"
        policy.save()

        event_payload = {
            "community": self.slack_community.metagov_slug,
            "initiator": {"user_id": "miriam", "provider": "discourse"},
            "source": "discourse",
            "event_type": "post_created",
            "data": {"title": "test", "raw": "post text", "category": 0},
        }

        # 2) Mimick an incoming notification from Metagov that the action has occurred
        client = Client()
        response = client.post(f"/metagov/internal/action", data=event_payload, content_type="application/json")

        self.assertEqual(response.status_code, 200)

        self.assertEqual(MetagovAction.objects.all().count(), 1)

        action = MetagovAction.objects.filter(event_type="discourse.post_created").first()

        # the action.community is the community that is connected to metagov
        self.assertEqual(action.community.platform, "slack")
        self.assertEqual(action.initiator.username, "discourse.miriam")
        self.assertEqual(action.initiator.metagovuser.external_username, "miriam")
        self.assertEqual(action.event_data["raw"], "post text")

        evaluation = PolicyEvaluation.objects.get(action=action, policy=policy)
        self.assertEqual(evaluation.data.get("test_verify_username"), "miriam")
        self.assertEqual(evaluation.status, PolicyEvaluation.PASSED)

    def test_metagov_slack_trigger(self):
        """Test receiving a Slack event from Metagov that creates a SlackPinMessage action"""
        # 1) Create Policy that is triggered by a metagov action
        policy = Policy(kind=Policy.PLATFORM)
        policy.community = self.slack_community
        policy.filter = """return action.action_type == 'slackpinmessage'"""
        policy.initialize = "pass"
        policy.notify = "pass"
        policy.check = "return PASSED"
        policy.success = "evaluation.data.set('got here', True)\ndebug('hello world!')"
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
        self.assertEqual(action.initiator.username, "alice")

        evaluation = PolicyEvaluation.objects.get(action=action, policy=policy)
        self.assertEqual(evaluation.data.get("got here"), True)
        self.assertEqual(evaluation.status, PolicyEvaluation.PASSED)

        # Check that evaluation debug log was generated
        self.assertEqual(EvaluationLog.objects.filter(evaluation=evaluation, msg__contains="hello world!").count(), 1)
