from django.contrib import admin
from django.contrib.admin import AdminSite
from govrules.models import CommunityIntegration, ProcessMeasure, RuleMeasure, ActionMeasure


class GovAdminSite(AdminSite):
    site_header = "GovBox"
    index_template = 'govadmin/index.html'
    login_template = 'govadmin/login.html'
    
    def has_permission(self, request):
        if request.user.is_anonymous:
            return False
        return True


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

