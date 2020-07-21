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

        proposed_constitutionactions = ConstitutionAction.objects.filter(community=user.community,
                                                               proposal__status=Proposal.PROPOSED)

        proposed_platformactions = PlatformAction.objects.filter(community=user.community,
                                                               proposal__status=Proposal.PROPOSED)


        self.children.append({'constitution_actions': [],
                              'platform_actions': []})
        for i in proposed_constitutionactions:
            self.children['constitution_actions'].append({
                                                     'description': str(i)
                                                     })

        for i in proposed_platformactions:
            self.children['platform_actions'].append({
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
            policies = PlatformPolicy.objects
        elif self.policy_type == "Constitution":
            policies = ConstitutionPolicy.objects

        policies = policies.filter(community=context['request'].user.community)

        for i in policies:
            self.children.append({'policy_type': self.policy_type,
                                  'is_bundled': i.is_bundled,
                                  'id': i.id,
                                  'filter': i.filter,
                                  'initialize': i.initialize,
                                  'check': i.check,
                                  'notify': i.notify,
                                  'success': i.success,
                                  'fail': i.fail,
                                  'description': i.description,
                                  'name': i.name})
