from jet.dashboard.modules import DashboardModule
from policyengine.models import *
from django.utils.translation import ugettext_lazy as _


class ProposedActions(DashboardModule):
       
    title = _('Proposed Actions')
    
    template = 'policyadmin/dashboard_modules/proposed_actions.html'
    
    layout = 'stacked'
    
    children = []
    draggable = False
    collapsible = True
    deletable = False
    show_title = True
    
    
    def init_with_context(self, context):
        user = context['request'].user
        
        proposed_processactions = ProcessAction.objects.filter(community=user.community,
                                                               proposal__status=Proposal.PROPOSED)
        
        proposed_communityactions = CommunityAction.objects.filter(community=user.community,
                                                               proposal__status=Proposal.PROPOSED)
        
        
        self.children.append({'process_actions': [],
                              'community_actions': []})   
        for i in proposed_processactions:
            self.children['process_actions'].append({
                                                     'description': str(i)
                                                     })
        
        for i in proposed_communityactions:
            self.children['community_actions'].append({
                                                     'description': str(i)
                                                     })
            
         
        
    

class RolePermissionModule(DashboardModule):
        
    title = _('Roles and Permissions')
    
    template = 'policyadmin/dashboard_modules/roles_permissions.html'
    
    layout = 'stacked'
    
    children = []
    draggable = False
    collapsible = True
    deletable = False
    show_title = True
    
    
    def init_with_context(self, context):
        user = context['request'].user
        roles = CommunityRole.objects.filter(community=user.community)
            
        for i in roles:
            role_info = {'role_name': i.name,
                         'permissions': [],
                         'users': []}
            for p in i.permissions.all():
                role_info['permissions'].append({'name': p.name})
                
            for u in i.user_set.all():
                cu = u.communityuser
                role_info['users'].append({'username': cu.readable_name})
            
            self.children.append(role_info)
        
    


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
    
    def __init__(self, policy_type="Community", title=None, **kwargs):
        kwargs.update({'policy_type': policy_type})
        super(PolicyModule, self).__init__(title, **kwargs)
        
    def settings_dict(self):
        return {
            'policy_type': self.policy_type,
        }


    def load_settings(self, settings):
        self.policy_type = settings.get('policy_type', self.policy_type)
        
    
    def init_with_context(self, context):
        if self.policy_type == "Community":
            policies = CommunityPolicy.objects
        elif self.policy_type == "Process":
            policies = ProcessPolicy.objects
        
        policies = policies.filter(community=context['request'].user.community)
            
        for i in policies:
            self.children.append({'policy_type': self.policy_type,
                                  'is_bundled': i.is_bundled,
                                  'id': i.id,
                                  'policy_filter_code': i.policy_filter_code,
                                  'policy_init_code': i.policy_init_code,
                                  'policy_notify_code': i.policy_notify_code,
                                  'policy_conditional_code': i.policy_conditional_code,
                                  'policy_action_code': i.policy_action_code,
                                  'policy_failure_code': i.policy_failure_code,
                                  'policy_text': i.policy_text,
                                  'explanation': i.explanation,
                                  'policy_name': i.policy_name})
        