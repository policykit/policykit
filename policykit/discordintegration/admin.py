from django.contrib import admin
from policyengine.admin import admin_site
from discordintegration.models import *

# Register your models here.

class DiscordPostMessageAdmin(admin.ModelAdmin):
    fields = ('text', 'channel', 'is_bundled')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.initiator = request.user
            obj.community = request.user.community
        obj.save()

admin_site.register(DiscordPostMessage, DiscordPostMessageAdmin)

class DiscordRenameChannelAdmin(admin.ModelAdmin):
    fields = ('channel', 'name', 'is_bundled')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.initiator = request.user
            obj.community = request.user.community
        obj.save()

admin_site.register(DiscordRenameChannel, DiscordRenameChannelAdmin)
