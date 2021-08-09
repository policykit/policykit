"""
Policy proposal tests that do NOT require Metagov to be enabled
"""
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from integrations.slack.models import SlackCommunity, SlackPinMessage, SlackUser
from policyengine.models import Proposal, Community, CommunityRole, Policy, PolicykitAddCommunityDoc
from policyengine.tasks import consider_proposed_actions

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

        # action initiated by user with "can_execute" should execute, and should NOT generate an proposal
        action = SlackPinMessage(initiator=user_with_can_execute, community=self.slack_community)
        self.govern_action_helper(action, expected_did_execute=True)

        # action initiated by user without "can_execute" should not execute, and should generate an proposal and fail because of the policy
        action = SlackPinMessage(initiator=self.user, community=self.slack_community)
        self.govern_action_helper(
            action, expected_policy=policy, expected_did_execute=False, expected_status=Proposal.FAILED
        )

    def govern_action_helper(self, action, expected_did_execute, expected_policy=None, expected_status=None):
        action._test_did_execute = False

        def mocked_execute():
            action._test_did_execute = True

        action.execute = mocked_execute
        action.save()
        self.assertEqual(action._test_did_execute, expected_did_execute)

        if expected_policy and expected_status:
            try:
                eval = Proposal.objects.get(action=action, policy=expected_policy)
            except:
                raise Exception(
                    f"Proposal not found! Expected action '{action}' to have a proposal for policy '{expected_policy}'"
                )
            self.assertEqual(eval.status, expected_status)
        else:
            # there shouldn't have been an proposal generated (meaning the initiator had can_execute perms)
            self.assertEqual(Proposal.objects.filter(action=action).count(), 0)

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
        self.govern_action_helper(
            action, expected_policy=first_policy, expected_did_execute=True, expected_status=Proposal.PASSED
        )

        # engine should not call "execute" for community actions on pass
        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        self.govern_action_helper(
            action, expected_policy=first_policy, expected_did_execute=False, expected_status=Proposal.PASSED
        )

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
        self.govern_action_helper(action, expected_did_execute=True)

        # action initiated by user without "can_execute" should not execute and not generate an proposal
        action = PolicykitAddCommunityDoc(name="my other doc", initiator=self.user, community=self.slack_community)
        self.govern_action_helper(action, expected_did_execute=False)

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
        self.govern_action_helper(action, expected_did_execute=False)

        # action initiated by user with "can_add" should pass
        user = SlackUser.objects.create(username="second-user", community=self.slack_community)
        can_add = Permission.objects.get(name="Can add policykit add community doc")
        user.user_permissions.add(can_add)
        self.assertTrue(user.has_perm("policyengine.add_policykitaddcommunitydoc"))
        action = PolicykitAddCommunityDoc(name="my other doc", initiator=user, community=self.slack_community)
        self.govern_action_helper(
            action, expected_policy=policy, expected_did_execute=True, expected_status=Proposal.PASSED
        )

    def test_policy_order(self):
        """Policies are tried in correct order"""
        first_policy = Policy.objects.create(
            **all_actions_pass_policy,
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="policy that passes",
        )

        # new action should pass
        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        self.govern_action_helper(
            action, expected_policy=first_policy, expected_did_execute=False, expected_status=Proposal.PASSED
        )

        second_policy = Policy.objects.create(
            **{**all_actions_pass_policy, "check": "return FAILED"},
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="policy that fails",
        )

        # new action should fail, because of most recent policy
        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        action.revert = lambda: None
        self.govern_action_helper(
            action, expected_policy=second_policy, expected_did_execute=False, expected_status=Proposal.FAILED
        )

        first_policy.description = "updated description"
        first_policy.save()
        # new action should pass, "first_policy" is now most recent
        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        self.govern_action_helper(
            action, expected_policy=first_policy, expected_did_execute=False, expected_status=Proposal.PASSED
        )

    def test_policy_exception(self):
        """Policies that raise exceptions are skipped"""
        all_pass_policy = Policy.objects.create(
            **all_actions_pass_policy,
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="all actions pass",
        )
        exception_policy = Policy.objects.create(
            **{
                **all_actions_pass_policy,
                "initialize": "proposal.data.set('was_executed', True)\nraise Exception('thrown from policy')",
            },
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="raises an exception",
        )

        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        self.govern_action_helper(
            action, expected_policy=all_pass_policy, expected_did_execute=False, expected_status=Proposal.PASSED
        )

        # test with falling back to a policy that fails

        all_fail_policy = Policy.objects.create(
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
        self.govern_action_helper(
            action, expected_policy=all_fail_policy, expected_did_execute=False, expected_status=Proposal.FAILED
        )

    def test_consider_proposed_actions(self):
        """Celery-scheduled consider_proposed_actions task works"""
        policy = Policy.objects.create(
            **{**all_actions_pass_policy, "check": "return None"},
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="all actions pending",
        )

        # Make a pending action
        action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        action.revert = lambda: None
        self.govern_action_helper(
            action, expected_policy=policy, expected_did_execute=False, expected_status=Proposal.PROPOSED
        )

        # Run the evaluator, just tests that it doesn't throw
        consider_proposed_actions()

        # Update the policy so the action passes now
        policy.check = "return PASSED"
        policy.save()

        consider_proposed_actions()

        eval = Proposal.objects.get(action=action, policy=policy)
        self.assertEqual(eval.status, Proposal.PASSED)