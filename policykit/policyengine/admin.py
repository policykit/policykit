from django.contrib import admin
from django.contrib.admin import AdminSite
from policyengine.models import *
from django.contrib.auth.models import User, Group, Permission
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy
from policykit.settings import PROJECT_NAME
import datetime
import logging


logger = logging.getLogger(__name__)


class PolicyAdminSite(AdminSite):
    site_title = PROJECT_NAME
    site_header = PROJECT_NAME
    
    index_title = gettext_lazy('Policy Authoring')
    
    index_template = 'policyadmin/index.html'
    login_template = 'policyadmin/login.html'
    
    def has_permission(self, request):
        if request.user.is_anonymous:
            return False
        return True
    
#     @never_cache
#     def index(self, request, extra_context=None):
#         """
#         Display the main admin index page, which lists all of the installed
#         apps that have been registered in this site.
#         """
#         app_list = self.get_app_list(request)
#         
#         user = request.user
#         community_integration = user.community_integration
# 
#         proposed_process_policies = ProcessPolicy.objects.filter(proposal__status=Proposal.PROPOSED, community_integration=community_integration)
# 
#         passed_process_policies = ProcessPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=community_integration)
# 
#         proposed_community_policies = CommunityPolicy.objects.filter(proposal__status=Proposal.PROPOSED, community_integration=community_integration)
# 
#        
# 
#         context = {**self.each_context(request), 
#                    'title': self.index_title, 
#                    'app_list': app_list, 
#                    'proposed_processes': proposed_process_policies,
#                    'passed_processes': passed_process_policies,
#                    'proposed_rules': proposed_community_policies,
#                    **(extra_context or {})}
# 
#         request.current_app = self.name
# 
#         return TemplateResponse(request, self.index_template or 'admin/index.html', context)


admin_site = PolicyAdminSite(name="policyadmin")


class PolicykitAddProcessPolicyAdmin(admin.ModelAdmin):
    fields= ('policy_filter_code', 'policy_init_code', 'policy_notify_code', 'policy_conditional_code', 'policy_action_code', 'policy_failure_code', 'policy_text', 'explanation', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        if not change:
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(PolicykitAddProcessPolicy, PolicykitAddProcessPolicyAdmin)


class PolicykitAddCommunityPolicyAdmin(admin.ModelAdmin):
    fields= ('policy_filter_code', 'policy_init_code', 'policy_notify_code', 'policy_conditional_code', 'policy_action_code', 'policy_failure_code', 'policy_text', 'explanation', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        if not change:
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(PolicykitAddCommunityPolicy, PolicykitAddCommunityPolicyAdmin)



class CommunityActionBundleAdmin(admin.ModelAdmin):
    fields= ('bundled_actions', 'bundle_type')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_bundle = True
            obj.community_origin = False
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(CommunityActionBundle, CommunityActionBundleAdmin)


class ProcessActionBundleAdmin(admin.ModelAdmin):
    fields= ('bundled_actions', 'bundle_type')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_bundle = True
            obj.community_origin = False
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(ProcessActionBundle, ProcessActionBundleAdmin)


class CommunityPolicyBundleAdmin(admin.ModelAdmin):
    fields= ('bundled_policies', 'explanation')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_bundle = True
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(CommunityPolicyBundle, CommunityPolicyBundleAdmin)



class ProcessPolicyBundleAdmin(admin.ModelAdmin):
    fields= ('bundled_policies', 'explanation')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_bundle = True
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(ProcessPolicyBundle, ProcessPolicyBundleAdmin)



class BooleanVoteAdmin(admin.ModelAdmin):
    fields= ('proposal', 'boolean_value')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        obj.save()

admin_site.register(BooleanVote, BooleanVoteAdmin)

class NumberVoteAdmin(admin.ModelAdmin):
    fields= ('proposal', 'number_value')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        obj.save()

admin_site.register(NumberVote, NumberVoteAdmin)


class PolicykitAddRoleAdmin(admin.ModelAdmin):

    fields= ('name', 'permissions','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community_integration = request.user.community_integration
        obj.save()
        
admin_site.register(PolicykitAddRole, PolicykitAddRoleAdmin)


class PolicykitDeleteRoleAdmin(admin.ModelAdmin):
    fields= ('role','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community_integration = request.user.community_integration
        obj.save()
        
admin_site.register(PolicykitDeleteRole, PolicykitDeleteRoleAdmin)


class PolicykitAddPermissionAdmin(admin.ModelAdmin):
    fields= ('role','permissions','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community_integration = request.user.community_integration
        obj.save()
        
admin_site.register(PolicykitAddPermission, PolicykitAddPermissionAdmin)


class PolicykitRemovePermissionAdmin(admin.ModelAdmin):
    fields= ('role','permissions','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community_integration = request.user.community_integration
        obj.save()
        
admin_site.register(PolicykitRemovePermission, PolicykitRemovePermissionAdmin)



class PolicykitAddUserRoleAdmin(admin.ModelAdmin):
    fields= ('role','users','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community_integration = request.user.community_integration
        obj.save()
        
admin_site.register(PolicykitAddUserRole, PolicykitAddUserRoleAdmin)

class PolicykitRemoveUserRoleAdmin(admin.ModelAdmin):
    fields= ('role','users','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community_integration = request.user.community_integration
        obj.save()
        
admin_site.register(PolicykitRemoveUserRole, PolicykitRemoveUserRoleAdmin)


class PolicykitChangeCommunityPolicyAdmin(admin.ModelAdmin):
    fields= ('community_policy', 'policy_filter_code', 'policy_init_code', 'policy_notify_code', 'policy_conditional_code', 'policy_action_code', 'policy_failure_code', 'policy_text', 'explanation', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(PolicykitChangeCommunityPolicy, PolicykitChangeCommunityPolicyAdmin)


class PolicykitChangeProcessPolicyAdmin(admin.ModelAdmin):
    fields= ('process_policy', 'policy_filter_code', 'policy_init_code', 'policy_notify_code', 'policy_conditional_code', 'policy_action_code', 'policy_failure_code', 'policy_text', 'explanation', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(PolicykitChangeProcessPolicy, PolicykitChangeProcessPolicyAdmin)


class PolicykitRemoveCommunityPolicyAdmin(admin.ModelAdmin):
    fields= ('community_policy','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community_integration = request.user.community_integration
        obj.save()
        
admin_site.register(PolicykitRemoveCommunityPolicy, PolicykitRemoveCommunityPolicyAdmin)


class PolicykitRemoveProcessPolicyAdmin(admin.ModelAdmin):
    fields= ('process_policy','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community_integration = request.user.community_integration
        obj.save()
        
admin_site.register(PolicykitRemoveProcessPolicy, PolicykitRemoveProcessPolicyAdmin)



class CommunityRoleAdmin(admin.ModelAdmin):
    fields= ('name', 'permissions')
    
    
    
#     def delete_model(self, request, object):
#         
#     
#     
    def save_model(self, request, obj, form, change):
        logger.info(request)
        logger.info(obj)
        logger.info(form)
        logger.info(change)
        obj.save()
        
        
 
admin_site.register(CommunityRole, CommunityRoleAdmin)


# 
# class ActionAdmin(admin.ModelAdmin):
#     pass
# 
# admin_site.register(ActionMeasure, ActionAdmin)
# 
# class CommunityIntegrationAdmin(admin.ModelAdmin):
#     pass
# 
# admin_site.register(CommunityIntegration, CommunityIntegrationAdmin)

