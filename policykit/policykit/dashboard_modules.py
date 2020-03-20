from jet.dashboard.modules import DashboardModule
from policyengine.models import CommunityPolicy, Proposal
from django.utils.translation import ugettext_lazy as _


class CommunityPolicyModule(DashboardModule):
    
    title = _('Passed Community Policies')
    
    template = 'policyadmin/dashboard_modules/community_policy.html'
    
    layout = 'stacked'
    
    children = []
    draggable = False
    collapsible = True
    deletable = False
    show_title = True
    
    
    def init_with_context(self, context):
        passed_community_policies = CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, 
                                                                   community_integration=context['request'].user.community_integration)
        for i in passed_community_policies:
            c = i.communitypolicybundle_set.all()
            if c.exists():
                c = c[0]
                i.bundle = c
            self.children.append({'is_bundled': i.is_bundled,
                                  'id': i.id})
        