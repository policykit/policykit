from jet.dashboard.modules import DashboardModule
from policyengine.models import CommunityPolicy, Proposal


class CommunityPolicyModule(DashboardModule):
    title = 'Community Policies'
    template = 'policyadmin/dashboard_modules/community_policy.html'

    def __init__(self, user):
        
        passed_community_policies = CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=user.community_integration)
        for i in passed_community_policies:
            c = i.communitypolicybundle_set.all()
            if c.exists():
                c = c[0]
                i.bundle = c
                
        self.children =  passed_community_policies