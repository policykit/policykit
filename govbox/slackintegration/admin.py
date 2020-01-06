from django.contrib import admin
from slackintegration.models import SlackIntegration, SlackUserGroup

# Register your models here.

class SlackIntegrationAdmin(admin.ModelAdmin):
    pass
admin.site.register(SlackIntegration, SlackIntegrationAdmin)


class SlackUserGroupAdmin(admin.ModelAdmin):
    pass
admin.site.register(SlackUserGroup, SlackUserGroupAdmin)