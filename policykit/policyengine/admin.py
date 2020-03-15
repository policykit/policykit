from django.contrib import admin
from django.contrib.admin import AdminSite
from policyengine.models import CommunityUser, ProcessPolicy, CommunityPolicy, CommunityPolicyBundle, CommunityActionBundle, Proposal, BooleanVote, NumberVote
from django.contrib.auth.models import User, Group, Permission
from policykit.forms import GroupAdminForm
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy
from policykit.settings import PROJECT_NAME
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
    
    @never_cache
    def index(self, request, extra_context=None):
        """
        Display the main admin index page, which lists all of the installed
        apps that have been registered in this site.
        """
        app_list = self.get_app_list(request)
        
        user = request.user
        community_integration = user.community_integration
        
        passed_process_policies = ProcessPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=community_integration)

        passed_community_policies = CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=community_integration)
        for i in passed_community_policies:
            c = i.communitypolicybundle_set.all()
            if c.exists():
                c = c[0]
                i.bundle = c


        context = {**self.each_context(request), 
                   'title': self.index_title, 
                   'app_list': app_list, 
                   'passed_processes': passed_process_policies,
                   'passed_rules': passed_community_policies,
                   **(extra_context or {})}

        request.current_app = self.name

        return TemplateResponse(request, self.index_template or 'admin/index.html', context)


admin_site = PolicyAdminSite(name="policyadmin")


class ProcessPolicyAdmin(admin.ModelAdmin):
    fields= ('policy_code', 'explanation')
    
    def save_model(self, request, obj, form, change):
        if not change:
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(ProcessPolicy, ProcessPolicyAdmin)

class CommunityPolicyAdmin(admin.ModelAdmin):
    fields= ('policy_filter_code', 'policy_init_code', 'policy_notify_code', 'policy_conditional_code', 'policy_action_code', 'policy_failure_code', 'policy_text', 'explanation', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        if not change:
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(CommunityPolicy, CommunityPolicyAdmin)

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


# Unregister the original Group admin.
admin.site.unregister(Group)

# Create a new Group admin.
class GroupAdmin(admin.ModelAdmin):
    # Use our custom form.
    form = GroupAdminForm
    # Filter permissions horizontal as well.
    filter_horizontal = ['permissions']

# Register the new Group ModelAdmin.
admin.site.register(Group, GroupAdmin)




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

