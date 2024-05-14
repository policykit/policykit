from rest_framework.test import APITestCase

import tests.utils as TestUtils

from policyengine.models import CommunityRole, Policy, CommunityDoc

class MembersAPITestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.slack_community, cls.user = TestUtils.create_slack_community_and_user()
        cls.community = cls.slack_community.community
        cls.constitution_community = cls.community.constitution_community

        # immediately pass all actions so we can assert their results immediately
        Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS,
            kind=Policy.CONSTITUTION,
            community=cls.community,
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


class DashboardAPITestCase(APITestCase):

    @classmethod
    def setUpTestData(cls):
        cls.slack_community, cls.user = TestUtils.create_slack_community_and_user()
        cls.community = cls.slack_community.community
        cls.constitution_community = cls.community.constitution_community

    def test_get_dashboard_handles_initial_community(self):
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        response = self.client.get('/api/dashboard')

        self.assertEqual(response.status_code, 200)
        body = response.data

        self.assertEqual(len(body['roles']), 2)
        self.assertEqual(body['roles'][0]['number_of_members'], 1)
        self.assertEqual(len(body['platform_policies']), 0)
        self.assertEqual(len(body['constitution_policies']), 0)
        self.assertEqual(len(body['proposals']), 0)
        self.assertEqual(len(body['community_docs']), 0)

    def test_get_dashboard_renders_platform_policy(self):
        policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS,
            kind=Policy.PLATFORM,
            community=self.community,
        )

        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        response = self.client.get('/api/dashboard')

        self.assertEqual(response.status_code, 200)
        body = response.data

        self.assertEqual(len(body['constitution_policies']), 0)
        self.assertEqual(len(body['platform_policies']), 1)
        self.assertEquals(body['platform_policies'][0]['name'], 'all actions pass')
        self.assertEquals(body['platform_policies'][0]['id'], policy.id)
        self.assertEquals(body['platform_policies'][0]['description'], None)

    def test_get_dashboard_renders_constitution_policy(self):
        policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS,
            kind=Policy.CONSTITUTION,
            community=self.community,
        )

        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        response = self.client.get('/api/dashboard')

        self.assertEqual(response.status_code, 200)
        body = response.data

        self.assertEqual(len(body['platform_policies']), 0)
        self.assertEqual(len(body['constitution_policies']), 1)
        self.assertEquals(body['constitution_policies'][0]['name'], 'all actions pass')
        self.assertEquals(body['constitution_policies'][0]['id'], policy.id)
        self.assertEquals(body['constitution_policies'][0]['description'], None)

    def test_get_dashboard_renders_passed_proposal_and_updates_member_count_of_role(self):
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PASS,
            kind=Policy.CONSTITUTION,
            community=self.community,
        )
        self._create_proposal()

        response = self.client.get('/api/dashboard')
        self.assertEqual(response.status_code, 200)
        body = response.data
        
        self.assertEqual(len(body['proposals']), 1)
        self.assertEqual(body['proposals'][0]['status'], 'passed')
        self.assertEqual(body['proposals'][0]['is_vote_closed'], True)
        self.assertEqual(body['proposals'][0]['action']['action_type'], 'policykitadduserrole')

        self.assertEqual(body['roles'][0]['number_of_members'], 2)

    def test_get_dashboard_renders_proposed_proposal(self):
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_PROPOSED,
            kind=Policy.CONSTITUTION,
            community=self.community,
        )
        self._create_proposal()

        response = self.client.get('/api/dashboard')
        self.assertEqual(response.status_code, 200)
        body = response.data
        
        self.assertEqual(len(body['proposals']), 1)
        self.assertEqual(body['proposals'][0]['status'], 'proposed')
        self.assertEqual(body['proposals'][0]['is_vote_closed'], False)
        self.assertEqual(body['proposals'][0]['action']['action_type'], 'policykitadduserrole')

    def test_get_dashboard_renders_failed_proposal(self):
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        policy = Policy.objects.create(
            **TestUtils.ALL_ACTIONS_FAIL,
            kind=Policy.CONSTITUTION,
            community=self.community,
        )
        self._create_proposal()

        response = self.client.get('/api/dashboard')
        self.assertEqual(response.status_code, 200)
        body = response.data
        
        self.assertEqual(len(body['proposals']), 1)
        self.assertEqual(body['proposals'][0]['status'], 'failed')
        self.assertEqual(body['proposals'][0]['is_vote_closed'], True)
        self.assertEqual(body['proposals'][0]['action']['action_type'], 'policykitadduserrole')

    def test_get_dashboard_renders_community_doc(self):
        self.client.force_login(user=self.user, backend="integrations.slack.auth_backends.SlackBackend")
        test_text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit. Nam
                interdum sodales vehicula. Vivamus quis ex sagittis, congue risus
                eget, efficitur justo. Maecenas posuere turpis eget laoreet
                suscipit. Ut ut venenatis sem. Ut vel orci ornare, tempor leo
                vitae, molestie nibh. Aliquam eget nulla dictum, mollis elit eu,
                ullamcorper ipsum. Morbi placerat malesuada justo, at consectetur
                neque ultrices eget. Nam dolor augue, rhoncus sit amet est id,
                faucibus pretium velit. Maecenas enim tellus, varius sed leo a,
                scelerisque consectetur nunc. Ut ipsum ligula, blandit eu augue et,
                viverra consectetur velit. In at tempor erat, a pulvinar orci. Ut
                vitae justo ut erat accumsan efficitur. Sed efficitur bibendum
                congue. Fusce nisi eros, pretium eget tellus at, vehicula pulvinar
                eros. Proin eu justo ac nibh tincidunt imperdiet eu sagittis augue. 
            """ 
        CommunityDoc.objects.create(
            name="test doc",
            text=test_text,
            community=self.community,
            is_active=True,
        )
        
        response = self.client.get('/api/dashboard')
        self.assertEqual(response.status_code, 200)
        body = response.data

        self.assertEqual(len(body['community_docs']), 1)
        self.assertEqual(body['community_docs'][0]['name'], 'test doc')
        self.assertEqual(body['community_docs'][0]['text'], test_text)

    def _create_proposal(self):
        # create a user and give them a role
        role = self.community.get_roles()[0]
        user_2 = TestUtils.create_user_in_slack_community(self.slack_community, "user_2")
        fixture_resp = self.client.put(
            '/api/members',
            data={'action': 'Add', 'role': role.id, 'members': [user_2.pk]},
            format='multipart'
        )
        self.assertEqual(fixture_resp.status_code, 200)



