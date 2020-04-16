from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import NoReverseMatch, reverse
from django.contrib.auth.models import User, Group, Permission
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import Http404, HttpResponseRedirect
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.translation import gettext_lazy
from policykit.settings import PROJECT_NAME
from policyengine.models import *
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
#         context = {**self.each_context(request), 
#                    'title': self.index_title, 
#                    'app_list': app_list,
#                    **(extra_context or {})}
#  
#         request.current_app = self.name
#  
#         return TemplateResponse(request, self.index_template or 'admin/index.html', context)


#     @never_cache
#     def login(self, request, extra_context=None):
#         """
#         Displays the login form for the given HttpRequest.
#         """
#         if request.method == 'GET' and self.has_permission(request):
#             # Already logged-in, redirect to admin index
#             index_path = reverse('admin:index', current_app=self.name)
#             return HttpResponseRedirect(index_path)
# 
#         from django.contrib.auth.views import LoginView
#         # Since this module gets imported in the application's root package,
#         # it cannot import models from other applications at the module level,
#         # and django.contrib.admin.forms eventually imports User.
#         from django.contrib.admin.forms import AdminAuthenticationForm
#         context = dict(
#             self.each_context(request),
#             title=_('Log in'),
#             app_path=request.get_full_path(),
#             username=request.user.get_username(),
#         )
#         if (REDIRECT_FIELD_NAME not in request.GET and
#                 REDIRECT_FIELD_NAME not in request.POST):
#             context[REDIRECT_FIELD_NAME] = reverse('admin:index', current_app=self.name)
#         context.update(extra_context or {})
#         
# 
#         defaults = {
#             'extra_context': context,
#             'authentication_form': self.login_form or AdminAuthenticationForm,
#             'template_name': self.login_template or 'admin/login.html',
#         }
#         request.current_app = self.name
#         return LoginView.as_view(**defaults)(request)





admin_site = PolicyAdminSite(name="policyadmin")


class PolicykitAddProcessPolicyAdmin(admin.ModelAdmin):
    fields= ('policy_filter_code', 'policy_init_code', 'policy_notify_code', 'policy_conditional_code', 'policy_action_code', 'policy_failure_code', 'policy_text', 'explanation', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitAddProcessPolicy, PolicykitAddProcessPolicyAdmin)


class PolicykitAddCommunityPolicyAdmin(admin.ModelAdmin):
    fields= ('policy_filter_code', 'policy_init_code', 'policy_notify_code', 'policy_conditional_code', 'policy_action_code', 'policy_failure_code', 'policy_text', 'explanation', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.community = request.user.community
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
            obj.community = request.user.community
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
            obj.community = request.user.community
        obj.save()

admin_site.register(ProcessActionBundle, ProcessActionBundleAdmin)


class CommunityPolicyBundleAdmin(admin.ModelAdmin):
    fields= ('bundled_policies', 'explanation')
    
    def save_model(self, request, obj, form, change):
        obj.is_bundle = True
        obj.community = request.user.community
        obj.save()

admin_site.register(CommunityPolicyBundle, CommunityPolicyBundleAdmin)



class ProcessPolicyBundleAdmin(admin.ModelAdmin):
    fields= ('bundled_policies', 'explanation')
    
    def save_model(self, request, obj, form, change):
        obj.is_bundle = True
        obj.community = request.user.community
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
        obj.community = request.user.community
        obj.save()
        
admin_site.register(PolicykitAddRole, PolicykitAddRoleAdmin)


class PolicykitDeleteRoleAdmin(admin.ModelAdmin):
    fields= ('role','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()
        
admin_site.register(PolicykitDeleteRole, PolicykitDeleteRoleAdmin)


class PolicykitAddPermissionAdmin(admin.ModelAdmin):
    fields= ('role','permissions','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()
        
admin_site.register(PolicykitAddPermission, PolicykitAddPermissionAdmin)


class PolicykitRemovePermissionAdmin(admin.ModelAdmin):
    fields= ('role','permissions','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()
        
admin_site.register(PolicykitRemovePermission, PolicykitRemovePermissionAdmin)



class PolicykitAddUserRoleAdmin(admin.ModelAdmin):
    fields= ('role','users','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()
        
admin_site.register(PolicykitAddUserRole, PolicykitAddUserRoleAdmin)

class PolicykitRemoveUserRoleAdmin(admin.ModelAdmin):
    fields= ('role','users','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()
        
admin_site.register(PolicykitRemoveUserRole, PolicykitRemoveUserRoleAdmin)


class PolicykitChangeCommunityPolicyAdmin(admin.ModelAdmin):
    fields= ('community_policy', 'policy_filter_code', 'policy_init_code', 'policy_notify_code', 'policy_conditional_code', 'policy_action_code', 'policy_failure_code', 'policy_text', 'explanation', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitChangeCommunityPolicy, PolicykitChangeCommunityPolicyAdmin)


class PolicykitChangeProcessPolicyAdmin(admin.ModelAdmin):
    fields= ('process_policy', 'policy_filter_code', 'policy_init_code', 'policy_notify_code', 'policy_conditional_code', 'policy_action_code', 'policy_failure_code', 'policy_text', 'explanation', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitChangeProcessPolicy, PolicykitChangeProcessPolicyAdmin)


class PolicykitRemoveCommunityPolicyAdmin(admin.ModelAdmin):
    fields= ('community_policy','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()
        
admin_site.register(PolicykitRemoveCommunityPolicy, PolicykitRemoveCommunityPolicyAdmin)


class PolicykitRemoveProcessPolicyAdmin(admin.ModelAdmin):
    fields= ('process_policy','is_bundled')
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()
        
admin_site.register(PolicykitRemoveProcessPolicy, PolicykitRemoveProcessPolicyAdmin)


class PolicykitChangeCommunityDocAdmin(admin.ModelAdmin):
    fields= ('community_doc', 'text',)
    
    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()
        
admin_site.register(PolicykitChangeCommunityDoc, PolicykitChangeCommunityDocAdmin)




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

