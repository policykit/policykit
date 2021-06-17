from unittest import skip

from django.contrib.auth.models import Permission
from django.test import Client, TestCase
import integrations.metagov.api as MetagovAPI
from integrations.metagov.models import MetagovProcess, MetagovPlatformAction
from integrations.slack.models import SlackCommunity, SlackPinMessage, SlackUser
from policyengine.models import (
    Community,
    CommunityRole,
    PlatformPolicy,
    ConstitutionPolicy,
    PolicykitAddCommunityDoc,
)

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
        can_add = Permission.objects.get(name="Can add slack pin message")
        user_group.permissions.add(can_add)
        community = Community.objects.create()
        self.slack_community = SlackCommunity.objects.create(
            community_name="my test community",
            community=community,
            team_id="TMQ3PKX",
            base_role=user_group,
        )
        self.user = SlackUser.objects.create(username="test", community=self.slack_community)

        # Activate a plugin to use in tests
        MetagovAPI.update_metagov_community(
            community=self.slack_community,
            plugins=list(
                [
                    {"name": "randomness", "config": {"default_low": 2, "default_high": 200}},
                    # {"name": "loomio", "config": {"api_key": ""}},
                ]
            ),
        )

    def test_can_execute(self):
        """Test that users with can_execute permissions can execute any action and mark it as 'passed'"""
        all_actions_fail_policy = {
            **all_actions_pass_policy,
            "check": "return FAILED",
        }
        policy = PlatformPolicy(
            **all_actions_fail_policy,
            community=self.slack_community,
            description="all actions fail",
            name="all actions fail",
        )
        policy.save()

        # create a test user with can_execute permissions
        can_execute = Permission.objects.get(name="Can execute slack pin message")
        can_add = Permission.objects.get(name="Can add slack pin message")
        user_with_can_execute = SlackUser.objects.create(username="powerful-user", community=self.slack_community)
        user_with_can_execute.user_permissions.add(can_add)
        user_with_can_execute.user_permissions.add(can_execute)

        # action initiated by user with "can_execute" should pass
        action = SlackPinMessage(initiator=user_with_can_execute, community=self.slack_community)
        action.execute = lambda: None  # don't do anything on execute
        action.save()
        self.assertEqual(action.proposal.status, "passed")

        # action initiated by user without "can_execute" should fail
        action = SlackPinMessage(initiator=self.user, community=self.slack_community)
        action.execute = lambda: None  # don't do anything on execute
        action.save()
        self.assertEqual(action.proposal.status, "failed")

    def test_can_execute_constitution(self):
        """Test that users with can_execute permissions can execute any constitution action and mark it as 'passed'"""
        all_actions_fail_policy = {
            **all_actions_pass_policy,
            "check": "return FAILED",
        }
        policy = ConstitutionPolicy(
            **all_actions_fail_policy,
            community=self.slack_community,
            description="all actions fail",
            name="all actions fail",
        )
        policy.save()

        # create a test user with can_execute permissions for PolicykitAddCommunityDoc
        can_add = Permission.objects.get(name="Can add policykit add community doc")
        can_execute = Permission.objects.get(name="Can execute policykit add community doc")
        user_with_can_execute = SlackUser.objects.create(username="powerful-user", community=self.slack_community)
        user_with_can_execute.user_permissions.add(can_add)
        user_with_can_execute.user_permissions.add(can_execute)
        self.assertTrue(user_with_can_execute.has_perm("policyengine.add_policykitaddcommunitydoc"))
        self.assertTrue(user_with_can_execute.has_perm("policyengine.can_execute_policykitaddcommunitydoc"))

        # action initiated by user with "can_execute" should pass
        action = PolicykitAddCommunityDoc(name="my doc", initiator=user_with_can_execute, community=self.slack_community)
        action.save()
        self.assertEqual(action.proposal.status, "passed")

        # action initiated by user without "can_execute" should fail
        action = PolicykitAddCommunityDoc(name="my other doc", initiator=self.user, community=self.slack_community)
        action.save()
        self.assertEqual(action.proposal.status, "failed")

    def test_cannot_propose_constitution(self):
        """Test that action fails when a user does not have permission to propose constitution change"""
        policy = ConstitutionPolicy(
            **all_actions_pass_policy,
            community=self.slack_community,
            description="all actions pass",
            name="all actions pass",
        )
        policy.save()

        # action initiated by user without "can_add" should fail
        user = SlackUser.objects.create(username="test-user", community=self.slack_community)
        self.assertEqual(user.has_perm("policyengine.add_policykitaddcommunitydoc"), False)
        action = PolicykitAddCommunityDoc(name="my doc", initiator=user, community=self.slack_community)
        action.save()
        action.refresh_from_db()  # test that it was saved to the db with correct proposal
        self.assertEqual(action.proposal.status, "failed")

        # action initiated by user with "can_add" should pass
        user = SlackUser.objects.create(username="second-user", community=self.slack_community)
        can_add = Permission.objects.get(name="Can add policykit add community doc")
        user.user_permissions.add(can_add)
        self.assertTrue(user.has_perm("policyengine.add_policykitaddcommunitydoc"))
        action = PolicykitAddCommunityDoc(name="my other doc", initiator=user, community=self.slack_community)
        action.save()
        action.refresh_from_db()  # test that it was saved to the db with correct proposal
        self.assertEqual(action.proposal.status, "passed")

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

    @skip("Don't run loomio vote test because it requires an API key")
    def test_loomio_vote(self):
        print("\nTesting external process\n")
        # 1) Create Policy and PlatformAction
        policy = PlatformPolicy()
        policy.community = self.slack_community
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
        action.community = self.slack_community

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

    def test_policy_order(self):
        first_policy = PlatformPolicy.objects.create(
            **all_actions_pass_policy,
            community=self.slack_community,
            name="policy that passes",
        )

        # new action should pass
        action = SlackPinMessage.objects.create(initiator=self.user, community=self.slack_community)
        self.assertEqual(action.proposal.status, "passed")

        second_policy = PlatformPolicy.objects.create(
            **{**all_actions_pass_policy, "check": "return FAILED"},
            community=self.slack_community,
            name="policy that fails",
        )

        # new action should fail, because of most recent policy
        action = SlackPinMessage.objects.create(initiator=self.user, community=self.slack_community)
        self.assertEqual(action.proposal.status, "failed")

        first_policy.description = "updated description"
        first_policy.save()
        # new action should pass, "first_policy" is now most recent
        action = SlackPinMessage.objects.create(initiator=self.user, community=self.slack_community)
        self.assertEqual(action.proposal.status, "passed")


class MetagovPlatformActionTest(TestCase):
    def setUp(self):
        user_group = CommunityRole.objects.create(role_name="fake role 2", name="testing role 2")
        p1 = Permission.objects.get(name="Can add slack pin message")
        user_group.permissions.add(p1)
        community = Community.objects.create()
        self.slack_community = SlackCommunity.objects.create(
            community_name="test community",
            community=community,
            team_id="test000",
            base_role=user_group,
        )

    def test_metagov_trigger(self):
        # 1) Create Policy that is triggered by a metagov action

        policy = PlatformPolicy()
        policy.community = self.slack_community
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

        self.assertEqual(MetagovPlatformAction.objects.all().count(), 1)

        action = MetagovPlatformAction.objects.filter(event_type="discourse.post_created").first()

        # the action.community is the community that is connected to metagov
        self.assertEqual(action.community.platform, "slack")
        self.assertEqual(action.initiator.username, "discourse.miriam")
        self.assertEqual(action.initiator.metagovuser.external_username, "miriam")
        self.assertEqual(action.data.get("test_verify_username"), "miriam")
        self.assertEqual(action.event_data["raw"], "post text")

        self.assertEqual(action.proposal.status, "passed")

    def test_metagov_slack_trigger(self):
        """Test receiving a Slack event from Metagov that creates a SlackPinMessage action"""
        # 1) Create Policy that is triggered by a metagov action
        policy = PlatformPolicy()
        policy.community = self.slack_community
        policy.filter = """return action.action_codename == 'slackpinmessage'"""
        policy.initialize = "pass"
        policy.notify = "pass"
        policy.check = "return PASSED"
        policy.success = "action.data.set('got here', True)"
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
        self.assertEqual(action.data.get("got here"), True)
        self.assertEqual(action.proposal.status, "passed")
