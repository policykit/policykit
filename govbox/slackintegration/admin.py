from django.contrib import admin
from govrules.admin import admin_site
from slackintegration.models import SlackIntegration, SlackUserGroup, SlackUser, SlackChat

# Register your models here.

class SlackIntegrationAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackIntegration, SlackIntegrationAdmin)


class SlackUserGroupAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackUserGroup, SlackUserGroupAdmin)


class SlackUserAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackUser, SlackUserAdmin)


class SlackChatAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackChat, SlackChatAdmin)
