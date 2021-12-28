from django.test import TestCase
from integrations.slack.models import SlackPinMessage
from policyengine.engine import EvaluationContext, PolicyCodeError, exec_code_block
from policyengine.models import Policy, Proposal
from django_db_logger.models import EvaluationLog
import policyengine.tests.utils as TestUtils
from policyengine.safe_exec_code import execute_user_code


class MyClass:
    value = 10

    def public_attr(self):
        return "foo"

    def _private_attr(self):
        return "bar"


class SafeExecCodeTests(TestCase):
    def test_execute_safe(self):
        """
        Test that permitted modules work in safe execution environment, and args and kwargs work.
        """
        example = """
def test(x, inst, name="alice"):
    random.randint(0, 10)

    # datetime module
    today = datetime.datetime.now()
    today.strftime('%Y-%m-%d')
    num_days = 5
    closing_at = (today + datetime.timedelta(days=num_days)).strftime('%Y-%m-%d')

    # time module
    datetime.time(hour=12, minute=34, second=56, microsecond=123456).isoformat(timespec='minutes')
    dt = datetime.time(hour=12, minute=34, second=56, microsecond=0)
    dt.isoformat(timespec='microseconds')

    # can access public attributes on class
    inst.public_attr
    inst.value

    datetime.timedelta(days=10)
    datetime.MAXYEAR
    y = 1
    for i in range(0,10):
        y += 2
    json.dumps({"foo": "bar"})
    base64.b64encode(b"testing")
    itertools.count(10)
    math.ceil(1.2)
    "hello world".replace(" ", "_")
    return name + " is " + str(x*x)
"""
        self.assertEqual(execute_user_code(example, "test", 5, MyClass()), "alice is 25")

    def test_execute_unsafe(self):
        """
        Test that import is restricted
        """
        example = """
import sys
def test(x, name="alice"):
    return name + " is " + str(x*x)
"""
        with self.assertRaises(SyntaxError) as cm:
            execute_user_code(example, "test", 5)
        self.assertTrue("Import statements are not allowed" in str(cm.exception))

    def test_execute_unsafe_access(self):
        """Test that getattr is restricted"""
        example = """
def test(inst):
    return inst._private_attr
"""

        with self.assertRaises(SyntaxError) as cm:
            execute_user_code(example, "test", MyClass())

    def test_execute_unsafe_access_2(self):
        """Test that write is restricted"""
        example = """
def test(inst):
    inst.value = 10
    return inst.value
"""

        with self.assertRaises(SyntaxError) as cm:
            execute_user_code(example, "test", MyClass())
        self.assertTrue("Restricted" in str(cm.exception))


class ExecCodeTests(TestCase):
    def setUp(self):
        self.slack_community, self.user = TestUtils.create_slack_community_and_user()

        self.policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PROPOSED,
            kind=Policy.PLATFORM,
            community=self.slack_community.community,
        )
        self.action = SlackPinMessage(initiator=self.user, community=self.slack_community, community_origin=True)
        self.action.revert = lambda: None
        self.action.execute = lambda: None
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
        self.assertRaises(PolicyCodeError, exec_code_block, "import os", ctx)

        self.assertEqual(exec_code_block("return slack.team_id", ctx), "ABC")

        # these shouldn't raise any exceptions
        exec_code_block("return action.id", ctx)
        exec_code_block("return policy.id", ctx)
        exec_code_block("return proposal.proposal_time", ctx)
        exec_code_block("return proposal.vote_url", ctx)
        exec_code_block("return datetime.datetime.now()", ctx)
        self.assertEqual(exec_code_block("return math.ceil(0.9)", ctx), 1)

    def test_syntax_errors(self):
        """syntax errors and other errors show correct line numbers"""
        ctx = EvaluationContext(self.proposal)
        with self.assertRaises(PolicyCodeError) as cm:
            exec_code_block("return variable_doesnt_exist", ctx)
        self.assertTrue("NameError at line 1" in str(cm.exception))

        with self.assertRaises(PolicyCodeError) as cm:
            exec_code_block("foo = 10\nimport something\nreturn True", ctx)
        self.assertTrue("SyntaxError at line 2" in str(cm.exception))

    def test_logger(self):
        """Test evaluation logger"""

        ctx = EvaluationContext(self.proposal)
        exec_code_block("logger.debug('hello')", ctx)
        self.assertEqual(EvaluationLog.objects.filter(proposal=self.proposal, msg__contains="hello").count(), 1)
        exec_code_block("logger.error('world')", ctx)
        self.assertEqual(EvaluationLog.objects.filter(proposal=self.proposal, msg__contains="world").count(), 1)
