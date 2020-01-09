from django.contrib import admin
from govrules.admin import admin_site
from slackintegration.models import SlackIntegration, SlackUserGroup, UserSignIn

# Register your models here.

class SlackIntegrationAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackIntegration, SlackIntegrationAdmin)


class SlackUserGroupAdmin(admin.ModelAdmin):
    pass
admin_site.register(SlackUserGroup, SlackUserGroupAdmin)

class UserSignInAdmin(admin.ModelAdmin):
    pass
admin_site.register(UserSignIn, UserSignInAdmin)