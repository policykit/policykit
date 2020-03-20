from jet.dashboard.modules import DashboardModule
from policyengine.models import CommunityPolicy, Proposal, ProcessPolicy
from django.utils.translation import ugettext_lazy as _


class PolicyModule(DashboardModule):
    
    title = _('Policies')
    
    template = 'policyadmin/dashboard_modules/community_policy.html'
    
    layout = 'stacked'
    
    children = []
    draggable = False
    collapsible = True
    deletable = False
    show_title = True
    
    policy_type = "Community"
    status = "passed"
    
    def __init__(self, policy_type="Community", status="passed", title=None, **kwargs):
        kwargs.update({'policy_type': policy_type,
                       'status': status})
        super(PolicyModule, self).__init__(title, **kwargs)
        
    def settings_dict(self):
        return {
            'policy_type': self.policy_type,
            'status': self.status
        }


    def load_settings(self, settings):
        self.policy_type = settings.get('policy_type', self.policy_type)
        self.status = settings.get('status', self.status)
        
    
    def init_with_context(self, context):
        if self.policy_type == "Community":
            policies = CommunityPolicy.objects
        elif self.policy_type == "Process":
            policies = ProcessPolicy.objects
        
        policies = policies.filter(community_integration=context['request'].user.community_integration)
    
        if self.status == "passed":
            policies = policies.filter(proposal__status=Proposal.PASSED)
        elif self.status == "proposed":
            policies = policies.filter(proposal__status=Proposal.PROPOSED)
            
            
            
        for i in policies:
            self.children.append({'policy_type': self.policy_type,
                                  'status': self.status,
                                  'is_bundled': i.is_bundled,
                                  'id': i.id,
                                  'policy_filter_code': i.policy_filter_code,
                                  'policy_init_code': i.policy_init_code,
                                  'policy_notify_code': i.policy_notify_code,
                                  'policy_conditional_code': i.policy_conditional_code,
                                  'policy_action_code': i.policy_action_code,
                                  'policy_failure_code': i.policy_failure_code,
                                  'policy_text': i.policy_text,
                                  'explanation': i.explanation})
        