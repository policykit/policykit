from django.test import TestCase
from policyengine.models import Policy, PolicyVariable, Proposal, ActionType
import tests.utils as TestUtils


class ClonePolicyTests(TestCase):
    """
    Test the policy cloning functionality
    """

    def setUp(self):
        self.slack_community_source, self.user = TestUtils.create_slack_community_and_user()
        self.community_source = self.slack_community_source.community
        self.constitution_community = self.community_source.constitution_community
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")

        # Create a policy to use as a source
        self.policy_source = Policy.objects.create(**TestUtils.ALL_ACTIONS_PASS, kind=Policy.TRIGGER, community=self.community_source, is_template=True)

        # Add an action type to source policy
        self.action_type = ActionType.objects.get_or_create(codename="slackpostmessage")[0]
        self.policy_source.action_types.set([ self.action_type ])

        # Create policy variables
        self.policy_variable_source = PolicyVariable.objects.create(name='test', label='Test', default_value="1", value="2", type='number', prompt='A test variable', policy=self.policy_source)

        # Create a community to attach policy copy to
        self.slack_community_source, user2 = TestUtils.create_slack_community_and_user(team_id="target", username="user2")
        self.community_target = self.slack_community_source.community

    def test_copy_policy_as_template(self):
        new_policy = self.policy_source.copy_as_template()

        # Check that policy copy was created
        self.assertNotEqual(new_policy.pk, self.policy_source.pk)

        # Check that new policy is a template
        self.assertTrue(new_policy.is_template)

        # Check that policy copy has the same values as original
        for fieldname in [ "kind", "filter", "initialize", "check", "notify", "success", "fail", "name", "description", "is_active" ]:
            self.assertEqual(getattr(new_policy, fieldname), getattr(self.policy_source, fieldname))

        # Check that the action_type was copied correctly
        self.assertEqual(new_policy.action_types.count(), 1)
        self.assertEqual(new_policy.action_types.all()[0].codename, "slackpostmessage")
        self.assertEqual(self.action_type.policy_set.count(), 2)

        # Check that policy variables were copied
        self.assertEqual(new_policy.variables.count(), 1)
        self.policy_variable_source.policy = self.policy_source

        # Check that policy copy has new instances of policy variables
        self.assertEqual(new_policy.variables.count(), 1)
        new_variable = new_policy.variables.all()[0]
        self.assertNotEqual(new_variable.pk, self.policy_variable_source.pk)

        for fieldname in [ "name", "label", "is_required", "default_value", "prompt", "type" ]:
            self.assertEqual(getattr(new_variable, fieldname), getattr(self.policy_variable_source, fieldname))

        # Check that policy variable value is set to the default value
        self.assertEqual(new_variable.value, self.policy_variable_source.default_value)

    def test_no_community_raises_exception(self):
        # Check that an exception is raied when copy_to_community() is used without a community parameter
        with self.assertRaisesRegexp(Exception, "Community object must be passed"):
            self.policy_source.copy_to_community()

    def test_not_template_policy_raises_exception(self):
        # Check that an exception is raied when copy_to_community() is used on a policy that is not designated as a template
        self.policy_source.is_template = False

        with self.assertRaisesRegexp(Exception, "Policy is not a template"):
            self.policy_source.copy_to_community(community=self.community_target)

    def test_copy_policy_to_community(self):
        new_policy = self.policy_source.copy_to_community(self.community_target)

        # Check that policy copy is related the target community
        self.assertEqual(new_policy.community, self.community_target)

        # Check that new policy is not a template
        self.assertFalse(new_policy.is_template)
    def test_copy_policy_with_variable_data(self):
        variable_value = "5"
        variable_data = { self.policy_variable_source.pk : variable_value }

        new_policy = self.policy_source.copy_to_community(community=self.community_target, variable_data=variable_data)

        # Check that policy variable has a value set from variable_data
        new_variable = new_policy.variables.all()[0]
        self.assertEqual(new_variable.value, variable_value)
