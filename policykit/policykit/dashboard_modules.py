from jet.dashboard.modules import DashboardModule
from policyengine.models import CommunityPolicy, Proposal


class CommunityPolicyModule(DashboardModule):
    template = 'policyadmin/dashboard_modules/community_policy.html'
    draggable = False
    collapsible = True
    deletable = False
    show_title = True
    title = 'Passed Community Policies'
    title_url = None
    
    def __init__(self, context=None, title=None, children=list(), **kwargs):
        
        passed_community_policies = CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, 
                                                                   community_integration=context.user.community_integration)
        for i in passed_community_policies:
            c = i.communitypolicybundle_set.all()
            if c.exists():
                c = c[0]
                i.bundle = c
        
        children = list(passed_community_policies)
        
        kwargs.update({'children': children})
        
        super(CommunityPolicyModule, self).__init__(title, **kwargs)

    def init_with_context(self, context):
        
        passed_community_policies = CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, 
                                                                   community_integration=context.user.community_integration)
        for i in passed_community_policies:
            c = i.communitypolicybundle_set.all()
            if c.exists():
                c = c[0]
                i.bundle = c
                
        self.children =  passed_community_policies
        