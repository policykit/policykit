from django.contrib import admin
from django.contrib.admin import AdminSite
from policyengine.models import CommunityIntegration, ProcessPolicy, RulePolicy, ActionPolicy, Policy, UserVote
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy
from govbox.settings import PROJECT_NAME
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
        
        passed_processes = ProcessPolicy.objects.filter(status=Policy.PASSED, community_integration=community_integration)

        passed_rules = RulePolicy.objects.filter(status=Policy.PASSED, community_integration=community_integration)

        context = {**self.each_context(request), 
                   'title': self.index_title, 
                   'app_list': app_list, 
                   'passed_processes': passed_processes,
                   'passed_rules': passed_rules,
                   **(extra_context or {})}

        request.current_app = self.name

        return TemplateResponse(request, self.index_template or 'admin/index.html', context)


admin_site = PolicyAdminSite(name="policyadmin")


class ProcessAdmin(admin.ModelAdmin):
    fields= ('process_code', 'explanation')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
            obj.community_integration = request.user.community_integration
            obj.status = Policy.PROPOSED
        obj.save()

admin_site.register(ProcessPolicy, ProcessAdmin)

class RuleAdmin(admin.ModelAdmin):
    fields= ('rule_code', 'rule_text', 'explanation')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
            obj.community_integration = request.user.community_integration
            obj.status = Policy.PROPOSED
        obj.save()

admin_site.register(RulePolicy, RuleAdmin)

class UserVoteAdmin(admin.ModelAdmin):
    fields= ('measure', 'value')
    
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

