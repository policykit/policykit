from constitution.models import (
    PolicykitAddConstitutionPolicy,
    PolicykitAddTriggerPolicy,
    PolicykitChangeConstitutionPolicy,
    PolicykitChangePlatformPolicy,
)
from django.test import TestCase
from policyengine.models import Policy, PolicyVariable, Proposal

import tests.utils as TestUtils


class PolicyActionSaveTests(TestCase):
    """
    Test the policy_action_save view
    """

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

    def test_change_constitution_policy(self):
        variable = PolicyVariable.objects.create(
            name='yes_votes_min',
            label='Minimum yes votes',
            default_value=1,
            value=2,
            type='number',
            prompt='Minimum yes votes to pass'
        )

        policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS, kind=Policy.CONSTITUTION, community=self.community
        )

        policy.variables.add(variable)

        response = self.client.post(
            "/main/policyengine/policy_action_save",
            data={
                "type": "Constitution",
                "operation": "Change",
                **TestUtils.ALL_ACTIONS_FAIL,
                "name": "updated",
                "action_types": ["policykitaddcommunitydoc", "policykitchangecommunitydoc"],
                "variables": { variable.pk: "10" },
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
        self.assertEqual(policy.variables.count(), 1)
        self.assertEqual(policy.variables.all()[0].value, "10")

    def test_add_trigger_policy(self):
        Policy.objects.create(**TestUtils.ALL_ACTIONS_PASS, kind=Policy.CONSTITUTION, community=self.community)

        response = self.client.post(
            "/main/policyengine/policy_action_save",
            data={
                "type": "Trigger",
                "operation": "Add",
                **TestUtils.ALL_ACTIONS_PASS,
                "name": "my trigger policy",
                "action_types": ["metagovtrigger"],
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        action = PolicykitAddTriggerPolicy.objects.get(community=self.constitution_community)

        # Check that proposal was created, and it passed
        proposal = Proposal.objects.get(action=action)
        self.assertEqual(proposal.status, Proposal.PASSED)

        # Check that policy was updated
        Policy.objects.get(name="my trigger policy", kind=Policy.TRIGGER)
