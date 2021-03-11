from django.test import TestCase
from django.contrib.auth.models import Permission
from policyengine.models import *
from integrations.slack.models import *
from datetime import datetime, timezone, timedelta

class ModelTestCase(TestCase):

    execute_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit edit role', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit add community doc', 'Can add policykit change community doc', 'Can add policykit delete community doc', 'Can execute policykit add role', 'Can execute policykit delete role', 'Can execute policykit edit role', 'Can execute policykit add user role', 'Can execute policykit remove user role', 'Can execute policykit change platform policy', 'Can execute policykit change constitution policy', 'Can execute policykit remove platform policy', 'Can execute policykit remove constitution policy', 'Can execute policykit add platform policy', 'Can execute policykit add constitution policy', 'Can execute policykit add community doc', 'Can execute policykit change community doc', 'Can execute policykit delete community doc']

    def setUp(self):
        self.starter_kit = StarterKit.objects.create(
            name='Test Kit',
            platform='slack'
        )
        self.role_default = CommunityRole.objects.create(
            role_name="base",
            name="base user"
        )
        for perm in self.execute_perms:
            self.role_default.permissions.add(Permission.objects.get(name=perm))
        self.community = SlackCommunity.objects.create(
            community_name='test',
            team_id='test',
            bot_id='test',
            access_token='test',
            base_role=self.role_default
        )
        self.role_default.community = self.community
        self.role_default.save()
        self.role_mod = CommunityRole.objects.create(
            role_name="mod",
            name="moderator",
            description="help the community follow its norms"
        )
        for perm in self.execute_perms:
            self.role_mod.permissions.add(Permission.objects.get(name=perm))
        self.role_mod.community = self.community
        self.role_mod.save()
        self.user1 = SlackUser.objects.create(
            readable_name='Test User 1',
            username="test1",
            community=self.community
        )
        self.role_mod.user_set.add(self.user1)
        self.role_mod.save()
        self.user2 = SlackUser.objects.create(
            username="test2",
            community=self.community
        )
        self.user3 = SlackUser.objects.create(
            username="test3",
            community=self.community
        )
        self.proposal = Proposal.objects.create(
            status=Proposal.PROPOSED,
            author=self.user1
        )
        self.booleanvote1 = BooleanVote.objects.create(
            proposal=self.proposal,
            user=self.user1,
            boolean_value=True
        )
        self.booleanvote2 = BooleanVote.objects.create(
            proposal=self.proposal,
            user=self.user2,
            boolean_value=True
        )
        self.booleanvote3 = BooleanVote.objects.create(
            proposal=self.proposal,
            user=self.user3,
            boolean_value=False
        )
        self.numbervote1 = NumberVote.objects.create(
            proposal=self.proposal,
            user=self.user1,
            number_value=2
        )
        self.numbervote2 = NumberVote.objects.create(
            proposal=self.proposal,
            user=self.user2,
            number_value=3
        )
        self.doc = CommunityDoc.objects.create(
            name='Test Doc',
            text='Insert text here',
            community=self.community
        )
        self.data_store = DataStore.objects.create(
            data_store=''
        )

class StarterKitTestCase(ModelTestCase):

    def test__str__(self):
        self.assertEqual(str(self.starter_kit), 'Test Kit')

class CommunityTestCase(ModelTestCase):

    def test__str__(self):
        self.assertEqual(str(self.community), 'test')

class CommunityRoleTestCase(ModelTestCase):

    def test__str__(self):
        self.assertEqual(str(self.role_default), 'base')

class CommunityUserTestCase(ModelTestCase):

    def test__str__(self):
        self.assertEqual(str(self.user1), 'Test User 1')
        self.assertEqual(str(self.user2), 'test2')

    def test_get_roles(self):
        roles = self.user1.get_roles()
        self.assertEqual(len(roles), 2)
        self.assertEqual(roles[0].role_name, 'base')
        self.assertEqual(roles[1].role_name, 'mod')

    def test_has_role(self):
        self.assertTrue(self.user1.has_role('base'))
        self.assertTrue(self.user1.has_role('mod'))
        self.assertTrue(self.user2.has_role('base'))
        self.assertFalse(self.user2.has_role('mod'))

class CommunityDocTestCase(ModelTestCase):

    def test__str__(self):
        self.assertEqual(str(self.doc), 'Test Doc')

class DataStoreTestCase(ModelTestCase):

    def test_all_functions(self):
        self.assertTrue(self.data_store.set('a', 'xyz'))
        self.assertEqual(self.data_store.get('a'), 'xyz')
        self.assertTrue(self.data_store.remove('a'))
        self.assertFalse(self.data_store.remove('a'))
        self.assertIsNone(self.data_store.get('a'))

class ProposalTestCase(ModelTestCase):

    def test_get_time_elapsed(self):
        time_elapsed = datetime.now(timezone.utc) - self.proposal.proposal_time
        difference = abs(self.proposal.get_time_elapsed() - time_elapsed)
        self.assertTrue(difference < timedelta(seconds=1))

    def test_get_all_boolean_votes(self):
        boolean_votes = self.proposal.get_all_boolean_votes()
        self.assertEqual(boolean_votes.count(), 3)

    def test_get_yes_votes(self):
        yes_votes = self.proposal.get_yes_votes()
        self.assertEqual(yes_votes.count(), 2)

    def test_get_no_votes(self):
        no_votes = self.proposal.get_no_votes()
        self.assertEqual(no_votes.count(), 1)

    def test_get_all_number_votes(self):
        number_votes = self.proposal.get_all_number_votes()
        self.assertEqual(number_votes.count(), 2)

    def test_get_one_number_votes(self):
        number_votes = self.proposal.get_one_number_votes(value=2)
        self.assertEqual(number_votes.count(), 1)

        number_votes = self.proposal.get_one_number_votes(value=0)
        self.assertEqual(number_votes.count(), 0)

class CommunityDocActionsTestCase(ModelTestCase):

    def setUp(self):
        super().setUp()

        self.action_add_doc = PolicykitAddCommunityDoc()
        self.action_add_doc.name='NewDoc'
        self.action_add_doc.text='Text in NewDoc'
        self.action_add_doc.community=self.community
        self.action_add_doc.initiator=self.user1

        self.action_change_doc = PolicykitChangeCommunityDoc()
        self.action_change_doc.name='EditedDoc'
        self.action_change_doc.text='Edits in NewDoc'
        self.action_change_doc.community=self.community
        self.action_change_doc.initiator=self.user1

        self.action_delete_doc = PolicykitDeleteCommunityDoc()
        self.action_delete_doc.community=self.community
        self.action_delete_doc.initiator=self.user1

    def test_add_doc__str__(self):
        self.assertEqual(str(self.action_add_doc), 'Add Document: NewDoc')

    def test_change_doc__str__(self):
        self.assertEqual(str(self.action_change_doc), 'Edit Document: EditedDoc')

    def test_all_doc_actions(self):
        self.action_add_doc.save()
        docs = CommunityDoc.objects.filter(name='NewDoc')
        self.assertEqual(docs.count(), 1)
        doc = docs[0]
        self.assertEqual(doc.name, 'NewDoc')
        self.assertEqual(doc.text, 'Text in NewDoc')

        self.action_change_doc.doc=CommunityDoc.objects.filter(name='NewDoc')[0]
        self.action_change_doc.save()
        docs = CommunityDoc.objects.filter(name='NewDoc')
        self.assertEqual(docs.count(), 0)
        docs = CommunityDoc.objects.filter(name='EditedDoc')
        self.assertEqual(docs.count(), 1)
        doc = docs[0]
        self.assertEqual(doc.name, 'EditedDoc')
        self.assertEqual(doc.text, 'Edits in NewDoc')

        self.action_delete_doc.doc=CommunityDoc.objects.filter(name='EditedDoc')[0]
        self.action_delete_doc.save()
        docs = CommunityDoc.objects.filter(name='EditedDoc')
        self.assertEqual(docs.count(), 0)

class RoleActionsTestCase(ModelTestCase):

    def setUp(self):
        super().setUp()

        self.action_add_role = PolicykitAddRole()
        self.action_add_role.name = 'senator'
        self.action_add_role.description = 'for the government'
        self.action_add_role.community = self.community
        self.action_add_role.initiator = self.user1

        self.action_edit_role = PolicykitEditRole()
        self.action_edit_role.name = 'president'
        self.action_edit_role.description = 'elected woohoo'
        self.action_edit_role.community = self.community
        self.action_edit_role.initiator = self.user1

        self.action_add_user_role = PolicykitAddUserRole()
        self.action_add_user_role.community = self.community
        self.action_add_user_role.initiator = self.user1

        self.action_remove_user_role = PolicykitRemoveUserRole()
        self.action_remove_user_role.community = self.community
        self.action_remove_user_role.initiator = self.user1

        self.action_delete_role = PolicykitDeleteRole()
        self.action_delete_role.community = self.community
        self.action_delete_role.initiator = self.user1

    def test_add_role__str__(self):
        self.assertEqual(str(self.action_add_role), 'Add Role: senator')

    def test_edit_role__str__(self):
        self.assertEqual(str(self.action_edit_role), 'Edit Role: president')

    def test_all_role_actions(self):
        self.action_add_role.save()
        for perm in self.execute_perms:
            self.action_add_role.permissions.add(Permission.objects.get(name=perm))
        self.action_add_role.ready = True
        self.action_add_role.save()
        roles = CommunityRole.objects.filter(role_name='senator')
        self.assertEqual(roles.count(), 1)
        role = roles[0]
        self.assertEqual(role.role_name, 'senator')
        self.assertEqual(role.description, 'for the government')

        self.action_add_user_role.role = role
        self.action_add_user_role.save()
        self.action_add_user_role.users.add(self.user3)
        self.action_add_user_role.ready = True
        self.action_add_user_role.save()
        self.assertTrue(self.user_3.has_role('senator'))

        self.action_edit_role.role = role
        self.action_edit_role.save()
        for perm in self.execute_perms:
            self.action_edit_role.permissions.add(Permission.objects.get(name=perm))
        self.action_edit_role.ready = True
        self.action_edit_role.save()
        roles = CommunityRole.objects.filter(role_name='senator')
        self.assertEqual(roles.count(), 0)
        roles = CommunityRole.objects.filter(role_name='president')
        self.assertEqual(roles.count(), 1)
        role = roles[0]
        self.assertEqual(role.role_name, 'president')
        self.assertEqual(role.description, 'elected woohoo')
        self.assertTrue(self.user_3.has_role('president'))
        self.assertFalse(self.user_3.has_role('senator'))

        self.action_remove_user_role.role = role
        self.action_remove_user_role.save()
        self.action_remove_user_role.users.add(self.user3)
        self.action_remove_user_role.ready = True
        self.action_remove_user_role.save()
        self.assertFalse(self.user_3.has_role('president'))

        self.action_delete_role.role = role
        self.action_delete_role.save()
        roles = CommunityRole.objects.filter(role_name='president')
        self.assertEqual(roles.count(), 0)

class UserVoteTestCase(ModelTestCase):

    def test_get_time_elapsed(self):
        time_elapsed = datetime.now(timezone.utc) - self.booleanvote1.vote_time
        difference = abs(self.booleanvote1.get_time_elapsed() - time_elapsed)
        self.assertTrue(difference < timedelta(seconds=1))

class BooleanVoteTestCase(ModelTestCase):

    def test__str__(self):
        self.assertEqual(str(self.booleanvote1), 'Test User 1 : True')
        self.assertEqual(str(self.booleanvote3), 'test3 : False')

class NumberVoteTestCase(ModelTestCase):

    def test__str__(self):
        self.assertEqual(str(self.numbervote1), 'Test User 1 : 2')
        self.assertEqual(str(self.numbervote2), 'test2 : 3')
