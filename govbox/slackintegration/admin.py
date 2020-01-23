from django.contrib import admin
from govrules.admin import admin_site
from slackintegration.models import SlackIntegration, SlackUser, SlackPostMessage, SlackScheduleMessage, SlackRenameConversation

# Register your models here.

class SlackIntegrationAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackIntegration, SlackIntegrationAdmin)


class SlackUserAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackUser, SlackUserAdmin)

class SlackPostMessageAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackPostMessage, SlackPostMessageAdmin)

class SlackScheduleMessageAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackScheduleMessage, SlackScheduleMessageAdmin)

class SlackRenameConversationAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackRenameConversation, SlackRenameConversationAdmin)

