from django.contrib import admin
from policyengine.admin import admin_site
from slackintegration.models import *

# Register your models here.

# class SlackIntegrationAdmin(admin.ModelAdmin):
#     pass
# admin_site.register(SlackIntegration, SlackIntegrationAdmin)
# 
# class SlackUserAdmin(admin.ModelAdmin):
#     pass
# admin_site.register(SlackUser, SlackUserAdmin)


class SlackPostMessageAdmin(admin.ModelAdmin):
    fields= ('text', 'channel', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.initiator = request.user
            obj.community = request.user.community
        obj.save()
    
admin_site.register(SlackPostMessage, SlackPostMessageAdmin)

class SlackScheduleMessageAdmin(admin.ModelAdmin):
    fields= ('text', 'channel', 'post_at', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.initiator = request.user
            obj.community = request.user.community
        obj.save()
    
admin_site.register(SlackScheduleMessage, SlackScheduleMessageAdmin)

class SlackRenameConversationAdmin(admin.ModelAdmin):
    fields= ('name', 'channel', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.initiator = request.user
            obj.community = request.user.community
        obj.save()
        
admin_site.register(SlackRenameConversation, SlackRenameConversationAdmin)

class SlackKickConversationAdmin(admin.ModelAdmin):
    fields= ('user', 'channel', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.initiator = request.user
            obj.community = request.user.community
        obj.save()
    
admin_site.register(SlackKickConversation, SlackKickConversationAdmin)

class SlackJoinConversationAdmin(admin.ModelAdmin):
    fields= ('users', 'channel', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.initiator = request.user
            obj.community = request.user.community
        obj.save()
        
admin_site.register(SlackJoinConversation, SlackJoinConversationAdmin)

class SlackPinMessageAdmin(admin.ModelAdmin):
    fields= ('channel', 'timestamp', 'is_bundled')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.initiator = request.user
            obj.community = request.user.community
        obj.save()
    
admin_site.register(SlackPinMessage, SlackPinMessageAdmin)

