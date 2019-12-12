from django.contrib import admin
from govrules.models import Community, Proposal, Post, Rule, CommunityIntegration, SlackIntegration, SlackUserGroup


class CommunityAdmin(admin.ModelAdmin):
    pass
admin.site.register(Community, CommunityAdmin)

class ProposalAdmin(admin.ModelAdmin):
    pass
admin.site.register(Proposal, ProposalAdmin)

class PostAdmin(admin.ModelAdmin):
    pass
admin.site.register(Post, PostAdmin)

class RuleAdmin(admin.ModelAdmin):
    pass
admin.site.register(Rule, RuleAdmin)

class CommunityIntegrationAdmin(admin.ModelAdmin):
    pass
admin.site.register(CommunityIntegration, CommunityIntegrationAdmin)

class SlackIntegrationAdmin(admin.ModelAdmin):
    pass
admin.site.register(SlackIntegration, SlackIntegrationAdmin)


class SlackUserGroupAdmin(admin.ModelAdmin):
    pass
admin.site.register(SlackUserGroup, SlackUserGroupAdmin)