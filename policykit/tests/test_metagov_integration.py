"""
Tests that require Metagov to be running.
Run with `INTEGRATION=1 python manage.py test`
"""
import os
import unittest

import integrations.metagov.api as MetagovAPI
from django.conf import settings
from django.contrib.auth.models import Permission
from django.test import LiveServerTestCase
from integrations.metagov.models import MetagovProcess
from integrations.slack.models import SlackCommunity, SlackPinMessage, SlackUser
from policyengine.models import Community, CommunityRole, PlatformPolicy

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
        """Integration-test metagov process with randomness plugin"""
        # 1) Create Policy and PlatformAction
        policy_code = {
            **all_actions_pass_policy,
            "initialize": """
metagov.start_process("randomness.delayed-stochastic-vote", {"options": ["one", "two", "three"], "delay": 1})
""",
            "check": """
result = metagov.close_process()
action.data.set('status', result.status)
action.data.set('outcome', result.outcome)

if result is None:
    return #still processing
if result.errors:
    return FAILED
if result.outcome:
    return PASSED if result.outcome.get('winner') else FAILED
return FAILED
""",
        }
        policy = PlatformPolicy(
            **policy_code,
            community=self.slack_community,
            description="test",
            name="test policy",
        )
        policy.save()

        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.slack_community

        # 2) Save action to trigger policy execution
        action.save()

        process = MetagovProcess.objects.filter(action=action, policy=policy).first()
        self.assertIsNotNone(process)

        self.assertEqual(action.proposal.status, "passed")
        self.assertEqual(action.data.get("status"), "completed")
        self.assertIsNotNone(action.data.get("outcome").get("winner"))

    def test_perform_action(self):
        """Integration-test metagov.perform_action function with randomness plugin"""
        # 1) Create Policy that performs a metagov action
        policy = PlatformPolicy()
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
        action.save()

        self.assertEqual(action.proposal.status, "passed")

        # Check that evaluation debug log was generated
        from django_db_logger.models import EvaluationLog

        self.assertEqual(EvaluationLog.objects.filter(community=policy.community, msg__contains="help!").count(), 1)
