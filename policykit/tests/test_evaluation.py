"""
Policy evaluation tests that do NOT require Metagov to be enabled
"""
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from integrations.slack.models import SlackCommunity, SlackPinMessage, SlackUser
from policyengine.models import Community, CommunityRole, Policy, PolicykitAddCommunityDoc

all_actions_pass_policy = {
    "filter": "return True",
    "initialize": "pass",
    "notify": "pass",
    "check": "return PASSED",
    "success": "pass",
    "fail": "pass",
}


class EvaluationTests(TestCase):
    @override_settings(METAGOV_ENABLED=False, METAGOV_URL="")
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

    def test_can_execute(self):
        """Test that users with can_execute permissions can execute any action and mark it as 'passed'"""
        all_actions_fail_policy = {
            **all_actions_pass_policy,
            "check": "return FAILED",
        }
        policy = Policy(
            **all_actions_fail_policy,
            kind=Policy.PLATFORM,
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

    def test_non_community_origin_actions(self):
        """Actions that didnt originate on the community platform should executed on 'pass'"""
        first_policy = Policy.objects.create(
            **all_actions_pass_policy,
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="policy that passes",
        )

        # engine should call "execute" for non-community actions on pass
        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=False)
        # mock the execute function
        action.execute = lambda: action.data.set("was_executed", True)
        action.save()
        self.assertEqual(action.proposal.status, "passed")
        self.assertEqual(action.data.get("was_executed"), True)

        # engine should not call "execute" for community actions on pass
        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        # mock the execute function
        action.execute = lambda: action.data.set("was_executed", True)
        action.save()
        self.assertEqual(action.proposal.status, "passed")
        self.assertEqual(action.data.get("was_executed"), None)

    def test_can_execute_constitution(self):
        """Test that users with can_execute permissions can execute any constitution action and mark it as 'passed'"""
        all_actions_fail_policy = {
            **all_actions_pass_policy,
            "check": "return FAILED",
        }
        policy = Policy(
            **all_actions_fail_policy,
            kind=Policy.CONSTITUTION,
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
        action = PolicykitAddCommunityDoc(
            name="my doc", initiator=user_with_can_execute, community=self.slack_community
        )
        action.save()
        self.assertEqual(action.proposal.status, "passed")

        # action initiated by user without "can_execute" should fail
        action = PolicykitAddCommunityDoc(name="my other doc", initiator=self.user, community=self.slack_community)
        action.save()
        self.assertEqual(action.proposal.status, "failed")

    def test_cannot_propose_constitution(self):
        """Test that action fails when a user does not have permission to propose constitution change"""
        policy = Policy(
            **all_actions_pass_policy,
            kind=Policy.CONSTITUTION,
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

    def test_policy_order(self):
        """Policies are tried in correct order"""
        first_policy = Policy.objects.create(
            **all_actions_pass_policy,
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="policy that passes",
        )

        # new action should pass
        action = SlackPinMessage.objects.create(
            initiator=self.user, community=self.slack_community, community_origin=True
        )
        self.assertEqual(action.proposal.status, "passed")

        second_policy = Policy.objects.create(
            **{**all_actions_pass_policy, "check": "return FAILED"},
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="policy that fails",
        )

        # new action should fail, because of most recent policy
        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        action.revert = lambda: None
        action.save()
        self.assertEqual(action.proposal.status, "failed")

        first_policy.description = "updated description"
        first_policy.save()
        # new action should pass, "first_policy" is now most recent
        action = SlackPinMessage.objects.create(
            initiator=self.user, community=self.slack_community, community_origin=True
        )
        self.assertEqual(action.proposal.status, "passed")

    def test_policy_exception(self):
        """Policies that raise exceptions are skipped"""
        Policy.objects.create(
            **all_actions_pass_policy,
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="all actions pass",
        )
        exception_policy = Policy.objects.create(
            **{
                **all_actions_pass_policy,
                "initialize": "action.data.set('was_executed', True)\nraise Exception('thrown from policy')",
            },
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="raises an exception",
        )

        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        action.revert = lambda: None
        action.save()
        # test that the exception policy was executed
        self.assertEqual(action.data.get("was_executed"), True)
        # test that we fell back to the all actions pass to ultimately pass the action
        self.assertEqual(action.proposal.status, "passed")

        # test with falling back to a policy that fails

        Policy.objects.create(
            **{**all_actions_pass_policy, "check": "return FAILED"},
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="all actions fail",
        )
        # re-save this policy so it becomes the most recent policy
        exception_policy.description = "updated description"
        exception_policy.save()

        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        action.revert = lambda: None
        action.save()
        self.assertEqual(action.data.get("was_executed"), True)
        self.assertEqual(action.proposal.status, "failed")