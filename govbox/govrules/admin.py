from django.contrib import admin
from govrules.models import Community, Proposal 


class CommunityAdmin(admin.ModelAdmin):
    pass
admin.site.register(Community, CommunityAdmin)

class ProposalAdmin(admin.ModelAdmin):
    pass
admin.site.register(Proposal, ProposalAdmin)