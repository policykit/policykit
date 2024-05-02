from rest_framework.test import APITestCase

import tests.utils as TestUtils

from policyengine.models import CommunityRole, Policy

class APIViewsTestCase(APITestCase):

    def setUp(self):
        self.slack_community, self.user = TestUtils.create_slack_community_and_user()
        self.community = self.slack_community.community
        self.constitution_community = self.community.constitution_community

        # immediately pass all actions so we can assert their results immediately
        Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS,
            kind=Policy.CONSTITUTION,
            community=self.community,
        )


    def test_get_members(self):
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        response = self.client.get('/api/members')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

        user_0 = response.data[0]
        self.assertEqual(user_0['id'], self.user.id)
        self.assertEqual(user_0['name'], 'user1')
        self.assertEqual(len(user_0['roles']), 1)
        self.assertEqual(user_0['roles'][0]['name'], 'fake role')

    def test_put_members_can_add_member_roles(self):
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        role = CommunityRole.objects.create(
            role_name="test role", community=self.community)
        user_2 = TestUtils.create_user_in_slack_community(self.slack_community, "user_2")
        user_3 = TestUtils.create_user_in_slack_community(self.slack_community, "user_3")
        
        # when a request is made to add 2 users to a role they do not have
        response = self.client.put(
            '/api/members',
            data={'action': 'Add', 'role': role.id, 'members': [user_2.pk, user_3.pk]},
            format='multipart'
        )
        self.assertEqual(response.status_code, 200)

        # then the new roles appear in the member list
        test_resp = self.client.get('/api/members')
        self.assertEqual(len(test_resp.data), 3)

        user_2_resp = next(u for u in test_resp.data if u['id'] == user_2.pk)
        self.assertIsNotNone(user_2_resp)
        user_2_role_ids = [r['id'] for r in user_2_resp['roles']]
        self.assertTrue(set(user_2_role_ids).issuperset({role.id}))

        user_3_resp = next(u for u in test_resp.data if u['id'] == user_3.pk)
        self.assertIsNotNone(user_3_resp)
        user_3_role_ids = [r['id'] for r in user_3_resp['roles']]
        self.assertTrue(set(user_3_role_ids).issuperset({role.id}))

    def test_put_members_can_remove_member_roles(self):
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        role = CommunityRole.objects.create(
            role_name="test role", community=self.community)
        user_2 = TestUtils.create_user_in_slack_community(self.slack_community, "user_2")
        user_3 = TestUtils.create_user_in_slack_community(self.slack_community, "user_3")
        
        # given users have the roles
        fixture_resp = self.client.put(
            '/api/members',
            data={'action': 'Add', 'role': role.id, 'members': [user_2.pk, user_3.pk]},
            format='multipart'
        )
        self.assertEqual(fixture_resp.status_code, 200)

        # when they are removed 
        resp = self.client.put(
            '/api/members',
            data={'action': 'Remove', 'role': role.id, 'members': [user_2.pk, user_3.pk]},
            format='multipart'
        )
        self.assertEqual(fixture_resp.status_code, 200)

        # then the new roles no longer appear in the member list
        test_resp = self.client.get('/api/members')
        self.assertEqual(len(test_resp.data), 3)

        user_2_resp = next(u for u in test_resp.data if u['id'] == user_2.pk)
        self.assertIsNotNone(user_2_resp)
        user_2_role_ids = [r['id'] for r in user_2_resp['roles']]
        self.assertTrue(set(user_2_role_ids).isdisjoint({role.id}))

        user_3_resp = next(u for u in test_resp.data if u['id'] == user_3.pk)
        self.assertIsNotNone(user_3_resp)
        user_3_role_ids = [r['id'] for r in user_3_resp['roles']]
        self.assertTrue(set(user_3_role_ids).isdisjoint({role.id}))

    def test_put_members_responds_400_on_invalid_body(self):
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        response = self.client.put(
            '/api/members',
            data={'action': 'foobar', 'role': 1, 'members': [1]},  # action is not 'Add' or 'Remove'
            format='multipart'
        )
        self.assertEqual(response.status_code, 400)

    def test_put_members_responds_404_if_role_exists_in_different_community(self):
        other_community, _ = TestUtils.create_slack_community_and_user(team_id="OTH", username="otheruser")
        role = CommunityRole.objects.create(
            role_name="other role", community=other_community.community)
        user_2 = TestUtils.create_user_in_slack_community(self.slack_community, "user_2")
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")

        # when a request is made to add 2 users to a role they do not have
        response = self.client.put(
            '/api/members',
            data={'action': 'Add', 'role': role.id, 'members': [user_2.pk]},
            format='multipart'
        )
        self.assertEqual(response.status_code, 404)

    def test_put_members_responds_404_if_user_exists_in_different_community(self):
        _, other_user = TestUtils.create_slack_community_and_user(team_id="OTH", username="otheruser")
        role = CommunityRole.objects.create(
            role_name="test role", community=self.community)

        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")

        # when a request is made to add 2 users to a role they do not have
        response = self.client.put(
            '/api/members',
            data={'action': 'Add', 'role': role.id, 'members': [other_user.pk]},
            format='multipart'
        )
        self.assertEqual(response.status_code, 404)

    def test_put_members_responds_403_on_anon_user(self):
        response = self.client.put(
            '/api/members',
            data={'action': 'Add', 'role': 1, 'members': [1]},  # action is missing
            format='multipart'
        )
        self.assertEqual(response.status_code, 403)
