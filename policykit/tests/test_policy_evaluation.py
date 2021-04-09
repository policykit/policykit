import json
from unittest import skip

import requests
from django.contrib.auth.models import Permission
from django.test import Client, TestCase
from integrations.metagov.library import update_metagov_community, metagov_slug
from integrations.metagov.models import ExternalProcess, MetagovPlatformAction, MetagovUser
from integrations.slack.models import SlackCommunity, SlackPinMessage, SlackStarterKit, SlackUser
from policyengine.models import CommunityRole, PlatformAction, PlatformPolicy, Proposal
from policyengine.views import check_policy, filter_policy


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
                ]
            ),
        )

    def test_close_process(self):
        # 1) Create Policy and PlatformAction
        policy = PlatformPolicy()
        policy.community = self.community
        policy.filter = "return True"
        policy.initialize = """
metagov.start_process("randomness.delayed-stochastic-vote", {"options": ["one", "two", "three"], "delay": 1})
"""
        policy.notify = ""
        policy.check = """
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
"""
        policy.success = "pass"
        policy.fail = "pass"
        policy.description = "test"
        policy.name = "test policy"
        policy.save()

        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.community

        # 2) Save action to trigger policy execution
        action.save()

        process = ExternalProcess.objects.filter(action=action, policy=policy).first()
        self.assertIsNotNone(process)

        # Fails because of bug https://github.com/amyxzhang/policykit/issues/305
        # self.assertEqual(action.proposal.status, "passed")

        self.assertEqual(action.data.get("status"), "completed")
        self.assertIsNotNone(action.data.get("outcome").get("winner"))

    @skip("Don't run loomio vote test because it requires an API key")
    def test_loomio_vote(self):
        print("\nTesting external process\n")
        # 1) Create Policy and PlatformAction
        policy = PlatformPolicy()
        policy.community = self.community
        policy.filter = "return True"
        policy.initialize = "pass"
        policy.notify = """
result = metagov.start_process("loomio.poll", {"title": "[test] policykit poll", "options": ["one", "two", "three"], "closing_at": "2021-05-11"})
poll_url = result.get('poll_url')
action.data.set('poll_url', poll_url)
"""
        policy.check = """
result = metagov.get_process_outcome()
if result is None:
    return #still processing
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

        process = ExternalProcess.objects.filter(action=action, policy=policy).first()
        self.assertIsNotNone(process)
        self.assertEqual(process.json_data, None)
        self.assertEqual(action.proposal.status, "proposed")
        self.assertTrue("https://www.loomio.org/p/" in action.data.get("poll_url"))

        # 3) Invoke callback URL to notify PolicyKit that process is complete
        # FIXME make this endpoint idempotent
        # FIXME used stored callback url instead of assuming

        client = Client()
        data = {
            "status": "completed",
            # 'errors': {'text': 'something went wrong'}
            "outcome": {"value": 27},
        }

        response = client.post(f"/metagov/outcome/{process.pk}", data=data, content_type="application/json")
        self.assertEqual(response.status_code, 200)

        process.refresh_from_db()
        action.refresh_from_db()
        policy.refresh_from_db()

        result_obj = json.loads(process.json_data)
        self.assertEqual(result_obj, data)

        result = check_policy(policy, action)
        self.assertEqual(result, "passed")

    def test_perform_action(self):
        print("\nTesting perform_action from metagov\n")
        # 1) Create Policy that performs a metagov action
        policy = PlatformPolicy()
        policy.community = self.community
        policy.filter = "return True"
        policy.initialize = "pass"
        policy.check = """parameters = {"low": 4, "high": 5}
response = metagov.perform_action('randomness.random-int', parameters)
if response and response.get('value') == 4:
    return PASSED
return FAILED"""
        policy.notify = "pass"
        policy.success = "action.execute()"  # Needed to mark as "passed" because of bug https://github.com/amyxzhang/policykit/issues/305
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


class MetagovPlatformActionTest(TestCase):
    def setUp(self):
        user_group = CommunityRole.objects.create(role_name="fake role", name="testing role")
        p1 = Permission.objects.get(name="Can add slack pin message")
        user_group.permissions.add(p1)
        self.community = SlackCommunity.objects.create(
            community_name="test community", team_id="test123", bot_id="test", access_token="test", base_role=user_group
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
        policy.success = "action.execute()"  # Needed to mark as "passed" because of bug https://github.com/amyxzhang/policykit/issues/305
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

        self.assertEqual(action.community.platform, "slack") ## the action.community is the community that is connected to metagov
        self.assertEqual(action.initiator.username, "discourse.miriam")
        self.assertEqual(action.initiator.metagovuser.external_username, "miriam")
        self.assertEqual(action.data.get("test_verify_username"), "miriam")
        self.assertEqual(action.event_data["raw"], "post text")

        self.assertEqual(action.proposal.status, "passed")
