from django.contrib.auth.models import Permission
from django.test import TestCase, override_settings
from integrations.slack.models import SlackCommunity, SlackPinMessage, SlackUser
from policyengine.engine import EvaluationContext, PolicyCodeError, exec_code_block
from policyengine.models import Community, CommunityRole, Policy, Proposal
from django_db_logger.models import EvaluationLog

all_actions_proposed_policy = {
    "filter": "return True",
    "initialize": "pass",
    "notify": "pass",
    "check": "return PROPOSED",
    "success": "pass",
    "fail": "pass",
}


class ExecCodeTests(TestCase):
    @override_settings(METAGOV_ENABLED=False, METAGOV_URL="")
    def setUp(self):
        user_group = CommunityRole.objects.create(role_name="fake role", name="testing role")
        can_add = Permission.objects.get(name="Can add slack pin message")
        user_group.permissions.add(can_add)
        community = Community.objects.create()
        self.slack_community = SlackCommunity.objects.create(
            community=community,
            team_id="TEST_TEAM_ID",
            base_role=user_group,
        )
        self.user = SlackUser.objects.create(username="test", community=self.slack_community)
        self.policy = Policy.objects.create(
            **all_actions_proposed_policy,
            kind=Policy.PLATFORM,
            community=self.slack_community,
            name="policy",
        )
        self.action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        self.action.save()
        self.proposal = Proposal.objects.create(action=self.action, policy=self.policy)

    def test_return_status(self):
        """Test the ability to return status"""

        ctx = EvaluationContext(self.proposal)
        self.assertEqual(exec_code_block("return PASSED", ctx), "passed")
        self.assertEqual(exec_code_block("return FAILED", ctx), "failed")
        self.assertEqual(exec_code_block("return PROPOSED", ctx), "proposed")

    def test_scope(self):
        """Test that all the EvaluationContext attributes are in scope"""

        ctx = EvaluationContext(self.proposal)

        self.assertRaises(PolicyCodeError, exec_code_block, "return variable_doesnt_exist", ctx)
        self.assertRaises(PolicyCodeError, exec_code_block, "return discord.team_id", ctx)

        self.assertEqual(exec_code_block("return slack.team_id", ctx), "TEST_TEAM_ID")

        # these shouldn't raise any exceptions
        exec_code_block("return action.id", ctx)
        exec_code_block("return policy.id", ctx)
        exec_code_block("return proposal.proposal_time", ctx)
        exec_code_block("return metagov.start_process", ctx)
        exec_code_block("import datetime", ctx)
        self.assertEqual(exec_code_block("import math\r\nreturn math.ceil(0.9)", ctx), 1)

    def test_logger(self):
        """Test evaluation logger"""

        ctx = EvaluationContext(self.proposal)
        exec_code_block("logger.debug('hello')", ctx)
        self.assertEqual(EvaluationLog.objects.filter(proposal=self.proposal, msg__contains="hello").count(), 1)
        exec_code_block("logger.error('world')", ctx)
        self.assertEqual(EvaluationLog.objects.filter(proposal=self.proposal, msg__contains="world").count(), 1)
