from django.contrib import admin
from django.contrib.admin import AdminSite
from policyengine.models import CommunityIntegration, ProcessPolicy, CommunityPolicy, CommunityAction, Proposal, UserVote
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

        context = {**self.each_context(request), 
                   'title': self.index_title, 
                   'app_list': app_list, 
                   'passed_processes': passed_process_policies,
                   'passed_rules': passed_community_policies,
                   **(extra_context or {})}

        request.current_app = self.name

        return TemplateResponse(request, self.index_template or 'admin/index.html', context)


admin_site = PolicyAdminSite(name="policyadmin")


class ProcessAdmin(admin.ModelAdmin):
    fields= ('policy_code', 'explanation')
    
    def save_model(self, request, obj, form, change):
        if not change:
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(ProcessPolicy, ProcessAdmin)

class CommunityAdmin(admin.ModelAdmin):
    fields= ('policy_conditional_code', 'policy_action_code', 'policy_text', 'explanation')
    
    def save_model(self, request, obj, form, change):
        if not change:
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community_integration = request.user.community_integration
        obj.save()

admin_site.register(CommunityPolicy, CommunityAdmin)

class UserVoteAdmin(admin.ModelAdmin):
    fields= ('policy', 'value')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        obj.save()

admin_site.register(UserVote, UserVoteAdmin)
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

