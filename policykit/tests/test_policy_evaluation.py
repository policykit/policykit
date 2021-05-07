import json
from unittest import skip

import requests
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from integrations.metagov.library import update_metagov_community, metagov_slug
from integrations.metagov.models import MetagovProcess, MetagovPlatformAction, MetagovUser
from integrations.slack.models import SlackCommunity, SlackPinMessage, SlackStarterKit, SlackUser
from policyengine.models import CommunityRole, PlatformAction, PlatformPolicy, Proposal
from policyengine.views import check_policy, filter_policy

all_actions_pass_policy = {
    "filter": "return True",
    "initialize": "pass",
    "notify": "pass",
    "check": "return PASSED",
    "success": "pass",
    "fail": "pass",
}


class EvaluationTests(TestCase):
    def setUp(self):
        # Set up a Slack community and a user
        user_group = CommunityRole.objects.create(role_name="fake role", name="testing role")
        p1 = Permission.objects.get(name="Can add slack pin message")
        user_group.permissions.add(p1)
        self.community = SlackCommunity.objects.create(
            community_name="my test community",
            team_id="TMQ3PKX",
            bot_id="test",
            access_token="test",
            base_role=user_group,
        )
        self.user = SlackUser.objects.create(username="test", community=self.community)

        # Activate a plugin to use in tests
        update_metagov_community(
            community=self.community,
            plugins=list(
                [
                    {"name": "randomness", "config": {"default_low": 2, "default_high": 200}},
                    # {"name": "loomio", "config": {"api_key": ""}},
                ]
            ),
        )

    def test_close_process(self):
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
            community=self.community,
            description="test",
            name="test policy",
        )
        policy.save()

        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.community

        # 2) Save action to trigger policy execution
        action.save()

        process = MetagovProcess.objects.filter(action=action, policy=policy).first()
        self.assertIsNotNone(process)

        self.assertEqual(action.proposal.status, "passed")
        self.assertEqual(action.data.get("status"), "completed")
        self.assertIsNotNone(action.data.get("outcome").get("winner"))

    @skip("Don't run loomio vote test because it requires an API key")
    def test_loomio_vote(self):
        print("\nTesting external process\n")
        # 1) Create Policy and PlatformAction
        policy = PlatformPolicy()
        policy.community = self.community
        policy.filter = "return True"
        policy.initialize = """
result = metagov.start_process("loomio.poll", {"title": "[test] policykit poll", "options": ["one", "two", "three"], "closing_at": "2021-05-11"})
poll_url = result.outcome.get('poll_url')
action.data.set('poll_url', poll_url)
"""
        policy.notify = "pass"
        policy.check = """
result = metagov.get_process()
if result.status != "completed":
    return None #still processing
if result.errors:
    return FAILED
if result.outcome:
    return PASSED if result.outcome.get('value') == 27 else FAILED
return FAILED
"""
        policy.success = "pass"
        policy.fail = "pass"
        policy.description = "test"
        policy.name = "test policy"
        policy.save()

        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.community

        # 2) Save action to trigger execution of check() and notify()
        action.save()

        process = MetagovProcess.objects.filter(action=action, policy=policy).first()
        self.assertIsNotNone(process)
        self.assertEqual(process.data.status, "pending")
        self.assertTrue("https://www.loomio.org/p/" in process.data.outcome.get("poll_url"))
        self.assertEqual(action.proposal.status, "proposed")
        self.assertTrue("https://www.loomio.org/p/" in action.data.get("poll_url"))

    def test_perform_action(self):
        print("\nTesting perform_action from metagov\n")
        # 1) Create Policy that performs a metagov action
        policy = PlatformPolicy()
        policy.community = self.community
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
        action.community = self.community
        action.save()

        self.assertEqual(action.proposal.status, "passed")

        # Check that evaluation debug log was generated
        from django_db_logger.models import EvaluationLog
        self.assertEqual(EvaluationLog.objects.filter(community=policy.community, msg__contains="help!").count(), 1)

    def test_policy_order(self):
        first_policy = PlatformPolicy.objects.create(
            **all_actions_pass_policy,
            community=self.community,
            name="policy that passes",
        )

        # new action should pass
        action = SlackPinMessage.objects.create(initiator=self.user, community=self.community)
        self.assertEqual(action.proposal.status, "passed")

        second_policy = PlatformPolicy.objects.create(
            **{**all_actions_pass_policy, "check": "return FAILED"},
            community=self.community,
            name="policy that fails",
        )

        # new action should fail, because of most recent policy
        action = SlackPinMessage.objects.create(initiator=self.user, community=self.community)
        self.assertEqual(action.proposal.status, "failed")

        first_policy.description = "updated description"
        first_policy.save()
        # new action should pass, "first_policy" is now most recent
        action = SlackPinMessage.objects.create(initiator=self.user, community=self.community)
        self.assertEqual(action.proposal.status, "passed")


class MetagovPlatformActionTest(TestCase):
    def setUp(self):
        user_group = CommunityRole.objects.create(role_name="fake role", name="testing role")
        p1 = Permission.objects.get(name="Can add slack pin message")
        user_group.permissions.add(p1)
        self.community = SlackCommunity.objects.create(
            community_name="test community",
            team_id="test123",
            bot_id="test",
            access_token="test",
            base_role=user_group,
        )

    def test_metagov_trigger(self):
        # 1) Create Policy that is triggered by a metagov action

        policy = PlatformPolicy()
        policy.community = self.community
        policy.filter = """return action.action_codename == 'metagovaction' \
and action.event_type == 'discourse.post_created'"""
        policy.initialize = "action.data.set('test_verify_username', action.initiator.metagovuser.external_username)"
        policy.notify = "pass"
        policy.check = "return PASSED if action.event_data['category'] == 0 else FAILED"
        policy.success = "pass"
        policy.fail = "pass"
        policy.description = "test"
        policy.name = "test policy"
        policy.save()

        event_payload = {
            "community": metagov_slug(self.community),
            "initiator": {"user_id": "miriam", "provider": "discourse"},
            "source": "discourse",
            "event_type": "post_created",
            "data": {"title": "test", "raw": "post text", "category": 0},
        }

        # 2) Mimick an incoming notification from Metagov that the action has occurred
        client = Client()
        response = client.post(f"/metagov/action", data=event_payload, content_type="application/json")

        self.assertEqual(response.status_code, 200)

        self.assertEqual(MetagovPlatformAction.objects.all().count(), 1)

        action = MetagovPlatformAction.objects.filter(event_type="discourse.post_created").first()

        # the action.community is the community that is connected to metagov
        self.assertEqual(action.community.platform, "slack")
        self.assertEqual(action.initiator.username, "discourse.miriam")
        self.assertEqual(action.initiator.metagovuser.external_username, "miriam")
        self.assertEqual(action.data.get("test_verify_username"), "miriam")
        self.assertEqual(action.event_data["raw"], "post text")

        self.assertEqual(action.proposal.status, "passed")
