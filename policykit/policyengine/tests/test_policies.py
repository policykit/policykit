from django.test import TestCase
from django.contrib.auth.models import Permission
from policyengine.models import *
from integrations.discord.models import *
from datetime import datetime, timezone, timedelta

class PolicyTestCase(TestCase):

    add_permms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add constitutionactionbundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit edit role', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit add community doc', 'Can add policykit change community doc', 'Can add policykit delete community doc']

    execute_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add constitutionactionbundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit edit role', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit add community doc', 'Can add policykit change community doc', 'Can add policykit delete community doc', 'Can execute policykit add role', 'Can execute policykit delete role', 'Can execute policykit edit role', 'Can execute policykit add user role', 'Can execute policykit remove user role', 'Can execute policykit change platform policy', 'Can execute policykit change constitution policy', 'Can execute policykit remove platform policy', 'Can execute policykit remove constitution policy', 'Can execute policykit add platform policy', 'Can execute policykit add constitution policy', 'Can execute policykit add community doc', 'Can execute policykit change community doc', 'Can execute policykit delete community doc']

    def setUp(self):
        self.role_default = CommunityRole.objects.create(
            role_name="base",
            name="base user"
        )
        for perm in self.add_perms:
            self.role_default.permissions.add(Permission.objects.get(name=perm))
        self.community = DiscordCommunity.objects.create(
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
        self.user_mod = DiscordUser.objects.create(
            readable_name='Test Mod',
            username="mod",
            community=self.community
        )
        self.role_mod.user_set.add(self.user_mod)
        self.role_mod.save()
        self.user_normal = DiscordUser.objects.create(
            readable_name='Test Normal',
            username="normal",
            community=self.community
        )
        action_add_policy = PolicykitAddConstitutionPolicy()
        action_add_policy.name = 'All Constitution Policies Pass'
        action_add_policy.description = 'all constitution policies pass'
        action_add_policy.filter = 'return True'
        action_add_policy.initialize = 'pass'
        action_add_policy.check = 'return PASSED'
        action_add_policy.notify = 'pass'
        action_add_policy.success = 'action.execute()'
        action_add_policy.fail = 'pass'
        action_add_policy.community = self.community
        action_add_policy.initiator = self.user_mod
        action_add_policy.save()
        action_add_policy = PolicykitAddPlatformPolicy()
        action_add_policy.name = 'All Platform Policies Pass'
        action_add_policy.description = 'all platform policies pass'
        action_add_policy.filter = 'return True'
        action_add_policy.initialize = 'pass'
        action_add_policy.check = 'return PASSED'
        action_add_policy.notify = 'pass'
        action_add_policy.success = 'action.execute()'
        action_add_policy.fail = 'pass'
        action_add_policy.community = self.community
        action_add_policy.initiator = self.user_mod
        action_add_policy.save()

        self.channel = '733209360549019691'

    def clear_messages(self):
        call_m = ('channels/%s/messages' % self.channel)
        messages = self.community.make_call(call_m)
        for m in messages:
            call_i = ('channels/%s/messages/%s' % (self.channel, m['id']))
            self.community.make_call(call_i, method='DELETE')

class Policy_FilterTestCase(PolicyTestCase):

    def setUp(self):
        super().setUp()

        action_add_policy = PolicykitAddPlatformPolicy()
        action_add_policy.name = 'Filter'
        action_add_policy.description = ''
        action_add_policy.filter = """
if action.action_type == "discordpostmessage":
    return True
""",
        action_add_policy.initialize = 'pass'
        action_add_policy.check = """
if action.text == "test":
    return FAILED
return PASSED
""",
        action_add_policy.notify = 'pass'
        action_add_policy.success = 'action.execute()'
        action_add_policy.fail = 'pass'
        action_add_policy.community = self.community
        action_add_policy.initiator = self.user_mod
        action_add_policy.save()

    def test_filter_allow(self):
        self.clear_messages()

        call = ('channels/%s/messages' % self.channel)
        data = {'content': 'abcd'}
        self.community.make_call(call, values=data)

        messages = self.community.make_call(call)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0]['content'], 'abcd')

    def test_filter_reject(self):
        self.clear_messages()

        call = ('channels/%s/messages' % self.channel)
        data = {'content': 'test'}
        self.community.make_call(call, values=data)

        messages = self.community.make_call(call)
        self.assertEqual(len(messages), 0)
