"""
Policy proposal tests that do NOT require Metagov to be enabled
"""
from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from integrations.slack.models import SlackPinMessage, SlackUser
from policyengine.models import CommunityRole, Proposal, Policy, ActionType
from constitution.models import PolicykitAddCommunityDoc, PolicykitAddRole
from policyengine.tasks import consider_proposed_actions
import policyengine.tests.utils as TestUtils


PROPOSE_COMMUNITY_DOC_PERM = "add_policykitaddcommunitydoc"
EXECUTE_COMMUNITIY_DOC_PERM = "can_execute_policykitaddcommunitydoc"


class EvaluationTests(TestCase):
    @override_settings(METAGOV_ENABLED=False, METAGOV_URL="")
    def setUp(self):
        self.slack_community, self.user = TestUtils.create_slack_community_and_user()
        self.community = self.slack_community.community
        self.constitution_community = self.community.constitution_community

    def new_slackpinmessage(self, initiator=None, community_origin=False):
        return SlackPinMessage(
            initiator=initiator or self.user, community=self.slack_community, community_origin=community_origin
        )

    def test_can_execute(self):
        """Test that users with can_execute permissions can execute any action and mark it as 'passed'"""
        policy = Policy.objects.create(**TestUtils.ALL_ACTIONS_FAIL, kind=Policy.PLATFORM, community=self.community)

        # create a test user with can_execute permissions
        can_execute = Permission.objects.get(name="Can execute slack pin message")
        user_with_can_execute = SlackUser.objects.create(username="powerful-user", community=self.slack_community)
        user_with_can_execute.user_permissions.add(can_execute)

        # action initiated by user with "can_execute" should execute, and should NOT generate an proposal
        action = self.new_slackpinmessage(initiator=user_with_can_execute)
        self.evaluate_action_helper(action, expected_did_execute=True)

        # action initiated by user without "can_execute" should not execute, and should generate an proposal and fail because of the policy
        action = self.new_slackpinmessage()

        self.evaluate_action_helper(
            action, expected_policy=policy, expected_did_execute=False, expected_status=Proposal.FAILED
        )

    def evaluate_action_helper(self, action, expected_did_execute, expected_policy=None, expected_status=None):
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
            **TestUtils.ALL_ACTIONS_PASS,
            kind=Policy.PLATFORM,
            community=self.community,
        )

        # engine should call "execute" for non-community actions on pass
        action = self.new_slackpinmessage()
        self.evaluate_action_helper(
            action, expected_policy=first_policy, expected_did_execute=True, expected_status=Proposal.PASSED
        )

        # engine should not call "execute" for community actions on pass
        action = self.new_slackpinmessage(community_origin=True)
        self.evaluate_action_helper(
            action, expected_policy=first_policy, expected_did_execute=False, expected_status=Proposal.PASSED
        )

    def test_can_execute_constitution(self):
        """Test that users with can_execute permissions can execute any constitution action and mark it as 'passed'"""
        policy = Policy(**TestUtils.ALL_ACTIONS_FAIL, kind=Policy.CONSTITUTION, community=self.community)
        policy.save()

        # create a test user with can_execute permissions for PolicykitAddCommunityDoc
        can_execute = Permission.objects.get(codename=EXECUTE_COMMUNITIY_DOC_PERM)
        user_with_can_execute = SlackUser.objects.create(username="powerful-user", community=self.slack_community)
        user_with_can_execute.user_permissions.add(can_execute)
        self.assertTrue(user_with_can_execute.has_perm(f"constitution.{PROPOSE_COMMUNITY_DOC_PERM}"))
        self.assertTrue(user_with_can_execute.has_perm(f"constitution.{EXECUTE_COMMUNITIY_DOC_PERM}"))

        # action initiated by user with "can_execute" should pass
        action = PolicykitAddCommunityDoc(
            name="my doc", initiator=user_with_can_execute, community=self.constitution_community
        )
        self.evaluate_action_helper(action, expected_did_execute=True)

        # action initiated by user without "can_execute" should generate a failed proposal
        action = PolicykitAddCommunityDoc(
            name="my other doc", initiator=self.user, community=self.constitution_community
        )
        self.evaluate_action_helper(
            action, expected_policy=policy, expected_did_execute=False, expected_status=Proposal.FAILED
        )

    def test_cannot_propose_constitution(self):
        """Test that action fails when a user does not have permission to propose constitution change"""
        policy = Policy(**TestUtils.ALL_ACTIONS_PASS, kind=Policy.CONSTITUTION, community=self.community)
        policy.save()

        # remove role from CommunityRole base role for this test
        base_role = CommunityRole.objects.get(community=self.community, is_base_role=True)

        can_add = Permission.objects.get(codename=PROPOSE_COMMUNITY_DOC_PERM)
        base_role.permissions.remove(can_add)
        base_role.save()

        # action initiated by user without "can_add" should fail
        user = SlackUser.objects.create(username="test-user", community=self.slack_community)
        self.assertEqual(user.has_perm(f"constitution.{PROPOSE_COMMUNITY_DOC_PERM}"), False)
        action = PolicykitAddCommunityDoc(name="my doc", initiator=user, community=self.constitution_community)
        self.evaluate_action_helper(action, expected_did_execute=False)

        # action initiated by user with "can_add" should pass
        user = SlackUser.objects.create(username="second-user", community=self.slack_community)
        user.user_permissions.add(can_add)
        self.assertTrue(user.has_perm(f"constitution.{PROPOSE_COMMUNITY_DOC_PERM}"))
        action = PolicykitAddCommunityDoc(name="my other doc", initiator=user, community=self.constitution_community)
        self.evaluate_action_helper(
            action, expected_policy=policy, expected_did_execute=True, expected_status=Proposal.PASSED
        )

        # add back removed perm
        base_role.permissions.add(can_add)
        base_role.save()

    def test_policy_order(self):
        """Policies are tried in correct order"""
        first_policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS,
            kind=Policy.PLATFORM,
            community=self.community,
        )

        # new action should pass
        action = self.new_slackpinmessage(community_origin=True)
        self.evaluate_action_helper(
            action, expected_policy=first_policy, expected_did_execute=False, expected_status=Proposal.PASSED
        )

        second_policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_FAIL,
            kind=Policy.PLATFORM,
            community=self.community,
        )

        # new action should fail, because of most recent policy
        action = self.new_slackpinmessage(community_origin=True)
        action.revert = lambda: None
        self.evaluate_action_helper(
            action, expected_policy=second_policy, expected_did_execute=False, expected_status=Proposal.FAILED
        )

        first_policy.description = "updated description"
        first_policy.save()
        # new action should pass, "first_policy" is now most recent
        action = self.new_slackpinmessage(community_origin=True)
        self.evaluate_action_helper(
            action, expected_policy=first_policy, expected_did_execute=False, expected_status=Proposal.PASSED
        )

    def test_action_type_filtering(self):
        """Policy is selected based on action_types"""
        slackpinmessage_policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS,
            kind=Policy.PLATFORM,
            community=self.community,
        )
        a = ActionType.objects.create(codename="slackpinmessage")
        slackpinmessage_policy.action_types.add(a)

        slackpostmessage_policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS,
            kind=Policy.PLATFORM,
            community=self.community,
        )
        a = ActionType.objects.create(codename="slackpostmessage")
        slackpostmessage_policy.action_types.add(a)

        # new action should pass using the slackpinmessage_policy
        action = self.new_slackpinmessage(community_origin=True)
        self.evaluate_action_helper(
            action, expected_policy=slackpinmessage_policy, expected_did_execute=False, expected_status=Proposal.PASSED
        )

    def test_policy_exception(self):
        """Policies that raise exceptions are skipped"""
        all_pass_policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS,
            kind=Policy.PLATFORM,
            community=self.community,
        )
        exception_policy = Policy.objects.create(
            **{
                **TestUtils.ALL_ACTIONS_PASS,
                "initialize": "proposal.data.set('was_executed', True)\nraise Exception('thrown from policy')",
                "name": "raises an exception",
            },
            kind=Policy.PLATFORM,
            community=self.community,
        )

        action = self.new_slackpinmessage(community_origin=True)
        self.evaluate_action_helper(
            action, expected_policy=all_pass_policy, expected_did_execute=False, expected_status=Proposal.PASSED
        )

        # test with falling back to a policy that fails

        all_fail_policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_FAIL,
            kind=Policy.PLATFORM,
            community=self.community,
        )
        # re-save this policy so it becomes the most recent policy
        exception_policy.description = "updated description"
        exception_policy.save()

        action = self.new_slackpinmessage(community_origin=True)
        action.revert = lambda: None
        self.evaluate_action_helper(
            action, expected_policy=all_fail_policy, expected_did_execute=False, expected_status=Proposal.FAILED
        )

    def test_consider_proposed_actions(self):
        """Celery-scheduled consider_proposed_actions task works"""
        policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PROPOSED,
            kind=Policy.PLATFORM,
            community=self.community,
        )

        # Make a pending action
        action = self.new_slackpinmessage(community_origin=True)
        action.revert = lambda: None
        self.evaluate_action_helper(
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

    def test_add_role(self):
        """Can evaluate PolicykitAddRole using evaluate_action"""
        all_fail_policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_FAIL,
            kind=Policy.CONSTITUTION,
            community=self.community,
        )

        action = PolicykitAddRole(initiator=self.user, community=self.constitution_community, name="new role")
        action.save(evaluate_action=False)

        self.assertEqual(Proposal.objects.filter(action=action).count(), 0)

        action.permissions.set(Permission.objects.all()[0:3])
        action.save(evaluate_action=True)

        proposal = Proposal.objects.get(action=action, policy=all_fail_policy)
        self.assertEqual(proposal.status, Proposal.FAILED)

        action.save()  # should do nothing
        proposal = Proposal.objects.get(action=action, policy=all_fail_policy)