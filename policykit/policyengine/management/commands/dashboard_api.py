
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Prefetch

from constitution.models import *
from policyengine.models import *
from integrations.slack.models import SlackUser
from policyengine.serializers import *

class Command(BaseCommand):
    help = 'Prints the CommunityDashboardSerializer data for a given slack user and logs the number of queries'
    def add_arguments(self, parser):
        parser.add_argument('name', type=str, help='Readbale name of the slack user')

    def handle(self, *args, **kwargs):
        self.stderr.write(self.style.NOTICE(f"Lookin up user: {kwargs['name']}"))
        user = SlackUser.objects.get(readable_name=kwargs['name'])
        self.stderr.write(self.style.NOTICE("Lookin up community"))
        # try prefetching to reduce number of queries
        community = Community.objects.prefetch_related(
            Prefetch("communityplatform_set", ConstitutionCommunity.objects.all(),),
            "communityrole_set__user_set",
            # "policy_set__proposal_set__governance_process",
            # Prefetch("policy_set", Policy.objects.prefetch_related('proposal_set')),
        ).get(communityplatform__communityuser__pk=user.pk)

        self.stderr.write(self.style.NOTICE("Getting serializer"))
        data = CommunityDashboardSerializer(community)
        self.stderr.write(self.style.NOTICE("Getting data"))
        data = data.data
        self.stderr.write(self.style.NOTICE("Returning response"))
        self.stderr.write(self.style.NOTICE(f"Number of Queries: {len(connection.queries)}"))
        self.stdout.write(str(data))


