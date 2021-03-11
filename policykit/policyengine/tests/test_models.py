from django.test import TestCase
from django.contrib.auth.models import Permission
from policyengine.models import *
from integrations.slack.models import *
from datetime import datetime, timezone, timedelta

class ProposalTestCase(TestCase):

    def setUp(self):
        user_group = CommunityRole.objects.create(
            role_name="fake role",
            name="testing role"
        )
        self.community = SlackCommunity.objects.create(
            community_name='test',
            team_id='test',
            bot_id='test',
            access_token='test',
            base_role=user_group
        )
        self.user1 = SlackUser.objects.create(
            username="test1",
            community=self.community
        )
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
