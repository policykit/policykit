from django.test import TestCase, override_settings
from policyengine.models import Proposal, Policy
from constitution.models import (
    PolicykitChangePlatformPolicy,
    PolicykitAddConstitutionPolicy,
    PolicykitChangeConstitutionPolicy,
    PolicyActionKind,
)
import policyengine.tests.utils as TestUtils


class PolicyActionSaveTests(TestCase):
    @override_settings(METAGOV_ENABLED=False, METAGOV_URL="")
    def setUp(self):
        self.slack_community, self.user = TestUtils.create_slack_community_and_user()
        self.community = self.slack_community.community
        self.constitution_community = self.community.constitution_community
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")

        # create a constitution policy to govern policy creation
        Policy.objects.create(**TestUtils.ALL_ACTIONS_PASS, kind=Policy.CONSTITUTION, community=self.community)

    def test_create_constitution_policy(self):
        response = self.client.post(
            "/main/policyengine/policy_action_save",
            data={
                "type": "Constitution",
                "operation": "Add",
                **TestUtils.ALL_ACTIONS_PASS,
                "name": "abc",
                "action_types": ["policykitaddcommunitydoc", "policykitchangecommunitydoc"],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        action = PolicykitAddConstitutionPolicy.objects.get(community=self.constitution_community)

        # Check that proposal was created, and it passed
        proposal = Proposal.objects.get(action=action)
        self.assertEqual(proposal.status, Proposal.PASSED)

        # Check that policy was created
        policy = Policy.objects.get(name="abc", community=self.community)
        self.assertEqual(policy.action_types.count(), 2)

    def test_change_platform_policy(self):
        policy = Policy.objects.create(**TestUtils.ALL_ACTIONS_PASS, kind=Policy.PLATFORM, community=self.community)

        response = self.client.post(
            "/main/policyengine/policy_action_save",
            data={
                "type": "Platform",
                "operation": "Change",
                **TestUtils.ALL_ACTIONS_FAIL,
                "name": "updated",
                "action_types": ["slackpinmessage", "slackpostmessage"],
                "policy": policy.pk,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        action = PolicykitChangePlatformPolicy.objects.get(community=self.constitution_community)

        # Check that proposal was created, and it passed
        proposal = Proposal.objects.get(action=action)
        self.assertEqual(proposal.status, Proposal.PASSED)

        # Check that policy was updated
        policy.refresh_from_db()
        self.assertEqual(policy.name, "updated")
        self.assertEqual(policy.action_types.count(), 2)

    def test_change_constitution_policy(self):
        policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS, kind=Policy.CONSTITUTION, community=self.community
        )

        response = self.client.post(
            "/main/policyengine/policy_action_save",
            data={
                "type": "Constitution",
                "operation": "Change",
                **TestUtils.ALL_ACTIONS_FAIL,
                "name": "updated",
                "action_types": ["policykitaddcommunitydoc", "policykitchangecommunitydoc"],
                "policy": policy.pk,
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        action = PolicykitChangeConstitutionPolicy.objects.get(community=self.constitution_community)

        # Check that proposal was created, and it passed
        proposal = Proposal.objects.get(action=action)
        self.assertEqual(proposal.status, Proposal.PASSED)

        # Check that policy was updated
        policy.refresh_from_db()
        self.assertEqual(policy.name, "updated")
        self.assertEqual(policy.action_types.count(), 2)

    def test_action_type_util(self):
        from policyengine.utils import get_action_types

        actions = get_action_types(self.community, [PolicyActionKind.CONSTITUTION])
        self.assertIsNotNone(actions["constitution"])
        actions = get_action_types(self.community, [PolicyActionKind.PLATFORM])
        self.assertIsNotNone(actions["slack"])
        actions = get_action_types(self.community, [PolicyActionKind.TRIGGER])
        self.assertIsNotNone(actions["metagov"])