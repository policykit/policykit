from django.contrib import admin
from django.contrib.admin import AdminSite
from govrules.models import Proposal, Post, Rule, CommunityIntegration


class GovAdminSite(AdminSite):
    site_header = "GovBox"
    index_template = 'govadmin/index.html'
    login_template = 'govadmin/login.html'
    
    def has_permission(self, request):
        if request.user.is_anonymous:
            return False
        return True


admin_site = GovAdminSite(name="govadmin")

class ProposalAdmin(admin.ModelAdmin):
    pass
admin_site.register(Proposal, ProposalAdmin)

class PostAdmin(admin.ModelAdmin):
    pass
admin_site.register(Post, PostAdmin)

class RuleAdmin(admin.ModelAdmin):
    pass
admin_site.register(Rule, RuleAdmin)

class CommunityIntegrationAdmin(admin.ModelAdmin):
    pass
admin_site.register(CommunityIntegration, CommunityIntegrationAdmin)

