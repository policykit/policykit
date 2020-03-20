from jet.dashboard.modules import DashboardModule
from policyengine.models import CommunityPolicy


class CommunityPolicyModule(DashboardModule):
    title = 'Community Policies'
    template = 'policyadmin/dashboard_modules/community_policy.html'

    def __init__(self):
        self.children = CommunityPolicy.objects.all()