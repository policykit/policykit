from django.test import TestCase
from policyengine.models import Policy

import tests.utils as TestUtils


class PolicyCommunityTests(TestCase):
    """
    Test policy create/save as it relates to the community field
    """
    def test_saving_policy_without_community_raises_exception(self):
      # Check that an exception is raied when a non-template policy is saved without a community
      with self.assertRaisesRegexp(Exception, "Non template policies must have a community"):
        Policy.objects.create(
          **TestUtils.ALL_ACTIONS_PROPOSED,
          kind=Policy.CONSTITUTION,
          is_template=False
        )

    def test_saving_template_policy_without_community(self):
      # Check that a template policy can be created without a community
      policy = Policy.objects.create(
        **TestUtils.ALL_ACTIONS_PROPOSED,
        kind=Policy.CONSTITUTION,
        is_template=True
      )

      self.assertEqual(policy.pk, 1)
