import json

from django.contrib.auth.models import Permission
from django.test import TestCase
from integrations.metagov.models import ExternalProcess
from integrations.slack.models import (SlackCommunity, SlackPinMessage,
                                       SlackStarterKit, SlackUser)
from policyengine.models import (CommunityRole, PlatformAction, PlatformPolicy,
                                 Proposal)
from policyengine.views import check_policy

"""
FIXME: mock metagov service
"""


class EvaluationTests(TestCase):
    def setUp(self):
        user_group = CommunityRole.objects.create(
            role_name="fake role", name="testing role")
        p1 = Permission.objects.get(name="Can add slack pin message")
        user_group.permissions.add(p1)
        self.community = SlackCommunity.objects.create(
            community_name='test',
            team_id='test',
            bot_id='test',
            access_token='test',
            base_role=user_group)
        self.user = SlackUser.objects.create(
            username="test", community=self.community)

    def test_external_process(self):
        print("\nTesting external process\n")
        # 1) Create Policy and PlatformAction
        policy = PlatformPolicy()
        policy.community = self.community
        policy.filter = "return True"
        policy.initialize = "pass"
        policy.notify = """
result = metagov.start_process("loomio", {"closing_at": "2021-05-11"})
poll_url = result.get('poll_url')
action.data.set('poll_url', poll_url)
"""
        policy.check = """
result = metagov.get_process_outcome()
if result is None:
    return #still processing
if result.errors:
    return FAILED
if result.outcome:
    return PASSED if result.outcome.get('value') == 27 else FAILED
return FAILED
"""
        policy.success = "pass"
        policy.fail = "pass"
        policy.description = "test"
        policy.name = "test policy"
        policy.save()

        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.community

        # 2) Save action to trigger execution of check() and notify()
        action.save()

        process = ExternalProcess.objects.filter(
            action=action, policy=policy).first()
        self.assertIsNotNone(process)
        self.assertEqual(process.json_data, None)
        self.assertEqual(action.proposal.status, "proposed")
        self.assertTrue(
            'https://www.loomio.org/p/' in action.data.get('poll_url'))

        # 3) Invoke callback URL to notify PolicyKit that process is complete
        # FIXME make this endpoint idempotent
        # FIXME used stored callback url instead of assuming
        from django.test import Client
        client = Client()
        data = {
            'status': 'completed',
            # 'errors': {'text': 'something went wrong'}
            'outcome': {'value': 27}
        }

        response = client.post(f"/metagov/outcome/{process.pk}", data=data, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        process.refresh_from_db()
        action.refresh_from_db()
        policy.refresh_from_db()

        result_obj = json.loads(process.json_data)
        self.assertEqual(result_obj, data)

        result = check_policy(policy, action)
        self.assertEqual(result, 'passed')

    def test_get_resource(self):
        print("\nTesting get_resource from metagov\n")
        # 1) Create Policy and PlatformAction
        policy = PlatformPolicy()
        policy.community = self.community
        policy.filter = "return True"
        policy.initialize = "pass"
        policy.check = """response = metagov.get_resource('cred', { 'username': 'miriam' })\n
cred = response.get('value')\n
return PASSED if cred > 0.5 else FAILED"""
        policy.notify = """pass"""
        policy.success = "pass"
        policy.fail = "pass"
        policy.description = "test"
        policy.name = "test policy"
        policy.save()

        action = SlackPinMessage()
        action.initiator = self.user
        action.community = self.community

        # 2) Save action to trigger execution of check() and notify()
        action.save()

        result = check_policy(policy, action)
        self.assertEqual(result, 'passed')
