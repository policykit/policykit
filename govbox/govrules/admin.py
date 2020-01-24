from django.contrib import admin
from django.contrib.admin import AdminSite
from govrules.models import CommunityIntegration, ProcessMeasure, RuleMeasure, ActionMeasure, Measure
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy
from govbox.settings import PROJECT_NAME


class GovAdminSite(AdminSite):
    site_title = PROJECT_NAME
    site_header = PROJECT_NAME
    
    index_title = gettext_lazy('Governance Authoring')
    
    index_template = 'govadmin/index.html'
    login_template = 'govadmin/login.html'
    
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
        
        passed_processes = ProcessMeasure.objects.filter(status=Measure.PASSED, community_integration=community_integration)

        passed_rules = RuleMeasure.objects.filter(status=Measure.PASSED, community_integration=community_integration)

        context = {**self.each_context(request), 
                   'title': self.index_title, 
                   'app_list': app_list, 
                   'passed_processes': passed_processes,
                   'passed_rules': passed_rules,
                   **(extra_context or {})}

        request.current_app = self.name

        return TemplateResponse(request, self.index_template or 'admin/index.html', context)


admin_site = GovAdminSite(name="govadmin")


class ProcessAdmin(admin.ModelAdmin):
    pass

admin_site.register(ProcessMeasure, ProcessAdmin)

class RuleAdmin(admin.ModelAdmin):
    pass

admin_site.register(RuleMeasure, RuleAdmin)

class ActionAdmin(admin.ModelAdmin):
    pass

admin_site.register(ActionMeasure, ActionAdmin)

class CommunityIntegrationAdmin(admin.ModelAdmin):
    pass

admin_site.register(CommunityIntegration, CommunityIntegrationAdmin)

