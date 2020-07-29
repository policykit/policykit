from django.contrib import admin
from django.contrib.admin import AdminSite
from django.urls import NoReverseMatch, reverse
from django.contrib.auth.models import User, Group, Permission
from django.views.decorators.cache import never_cache
from django.template.response import TemplateResponse
from django.http import Http404, HttpResponseRedirect
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.utils.translation import gettext_lazy
from policykit.settings import PROJECT_NAME
from policyengine.models import *
import datetime
import logging


logger = logging.getLogger(__name__)


class PolicyAdminSite(AdminSite):
    site_title = PROJECT_NAME
    site_header = PROJECT_NAME

    index_title = gettext_lazy('Policy Authoring')

    index_template = 'policyadmin/index.html'
    login_template = 'policyadmin/login.html'

    def has_permission(self, request):
        if request.user.is_anonymous:
            return False
        return True

#     @never_cache
#     def index(self, request, extra_context=None):
#         """
#         Display the main admin index page, which lists all of the installed
#         apps that have been registered in this site.
#         """
#         app_list = self.get_app_list(request)
#
#         context = {**self.each_context(request),
#                    'title': self.index_title,
#                    'app_list': app_list,
#                    **(extra_context or {})}
#
#         request.current_app = self.name
#
#         return TemplateResponse(request, self.index_template or 'admin/index.html', context)


#     @never_cache
#     def login(self, request, extra_context=None):
#         """
#         Displays the login form for the given HttpRequest.
#         """
#         if request.method == 'GET' and self.has_permission(request):
#             # Already logged-in, redirect to admin index
#             index_path = reverse('admin:index', current_app=self.name)
#             return HttpResponseRedirect(index_path)
#
#         from django.contrib.auth.views import LoginView
#         # Since this module gets imported in the application's root package,
#         # it cannot import models from other applications at the module level,
#         # and django.contrib.admin.forms eventually imports User.
#         from django.contrib.admin.forms import AdminAuthenticationForm
#         context = dict(
#             self.each_context(request),
#             title=_('Log in'),
#             app_path=request.get_full_path(),
#             username=request.user.get_username(),
#         )
#         if (REDIRECT_FIELD_NAME not in request.GET and
#                 REDIRECT_FIELD_NAME not in request.POST):
#             context[REDIRECT_FIELD_NAME] = reverse('admin:index', current_app=self.name)
#         context.update(extra_context or {})
#
#
#         defaults = {
#             'extra_context': context,
#             'authentication_form': self.login_form or AdminAuthenticationForm,
#             'template_name': self.login_template or 'admin/login.html',
#         }
#         request.current_app = self.name
#         return LoginView.as_view(**defaults)(request)





admin_site = PolicyAdminSite(name="policyadmin")


class PolicykitAddConstitutionPolicyAdmin(admin.ModelAdmin):
    fields = ('name', 'description', 'is_bundled', 'filter', 'initialize', 'check', 'notify', 'success', 'fail')

    def save_model(self, request, obj, form, change):
        obj.community = request.user.community
        obj.initiator = request.user
        obj.save()

admin_site.register(PolicykitAddConstitutionPolicy, PolicykitAddConstitutionPolicyAdmin)


class PolicykitAddPlatformPolicyAdmin(admin.ModelAdmin):
    fields = ('name', 'description', 'is_bundled', 'filter', 'initialize', 'check', 'notify', 'success', 'fail')

    def save_model(self, request, obj, form, change):
        obj.community = request.user.community
        obj.initiator = request.user
        obj.save()

admin_site.register(PolicykitAddPlatformPolicy, PolicykitAddPlatformPolicyAdmin)



class PlatformActionBundleAdmin(admin.ModelAdmin):
    fields= ('bundled_actions', 'bundle_type')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_bundle = True
            obj.platform_origin = False
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community = request.user.community
        obj.save()

admin_site.register(PlatformActionBundle, PlatformActionBundleAdmin)


class ConstitutionActionBundleAdmin(admin.ModelAdmin):
    fields= ('bundled_actions', 'bundle_type')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.is_bundle = True
            obj.platform_origin = False
            p = Proposal.objects.create(author=request.user, status=Proposal.PROPOSED)
            obj.proposal = p
            obj.community = request.user.community
        obj.save()

admin_site.register(ConstitutionActionBundle, ConstitutionActionBundleAdmin)


class PlatformPolicyBundleAdmin(admin.ModelAdmin):
    fields= ('bundled_policies', 'description')

    def save_model(self, request, obj, form, change):
        obj.is_bundle = True
        obj.community = request.user.community
        obj.save()

admin_site.register(PlatformPolicyBundle, PlatformPolicyBundleAdmin)



class ConstitutionPolicyBundleAdmin(admin.ModelAdmin):
    fields= ('bundled_policies', 'description')

    def save_model(self, request, obj, form, change):
        obj.is_bundle = True
        obj.community = request.user.community
        obj.save()

admin_site.register(ConstitutionPolicyBundle, ConstitutionPolicyBundleAdmin)



class BooleanVoteAdmin(admin.ModelAdmin):
    fields= ('proposal', 'boolean_value')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        obj.save()

admin_site.register(BooleanVote, BooleanVoteAdmin)

class NumberVoteAdmin(admin.ModelAdmin):
    fields= ('proposal', 'number_value')

    def save_model(self, request, obj, form, change):
        if not change:
            obj.user = request.user
        obj.save()

admin_site.register(NumberVote, NumberVoteAdmin)


class PolicykitAddRoleAdmin(admin.ModelAdmin):
    fields= ('name', 'permissions','is_bundled')

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitAddRole, PolicykitAddRoleAdmin)


class PolicykitDeleteRoleAdmin(admin.ModelAdmin):
    fields= ('role','is_bundled')

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitDeleteRole, PolicykitDeleteRoleAdmin)


class PolicykitAddPermissionAdmin(admin.ModelAdmin):
    fields= ('role','permissions','is_bundled')

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitAddPermission, PolicykitAddPermissionAdmin)


class PolicykitRemovePermissionAdmin(admin.ModelAdmin):
    fields= ('role','permissions','is_bundled')

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitRemovePermission, PolicykitRemovePermissionAdmin)



class PolicykitAddUserRoleAdmin(admin.ModelAdmin):
    fields= ('role','users','is_bundled')

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitAddUserRole, PolicykitAddUserRoleAdmin)

class PolicykitRemoveUserRoleAdmin(admin.ModelAdmin):
    fields= ('role','users','is_bundled')

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitRemoveUserRole, PolicykitRemoveUserRoleAdmin)


class PolicykitChangePlatformPolicyAdmin(admin.ModelAdmin):
    fields = ('name', 'description', 'is_bundled', 'filter', 'initialize', 'check', 'notify', 'success', 'fail')

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitChangePlatformPolicy, PolicykitChangePlatformPolicyAdmin)


class PolicykitChangeConstitutionPolicyAdmin(admin.ModelAdmin):
    fields = ('name', 'description', 'is_bundled', 'filter', 'initialize', 'check', 'notify', 'success', 'fail')

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitChangeConstitutionPolicy, PolicykitChangeConstitutionPolicyAdmin)


class PolicykitRemovePlatformPolicyAdmin(admin.ModelAdmin):
    fields= ('platform_policy','is_bundled')

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitRemovePlatformPolicy, PolicykitRemovePlatformPolicyAdmin)


class PolicykitRemoveConstitutionPolicyAdmin(admin.ModelAdmin):
    fields= ('constitution_policy','is_bundled')

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitRemoveConstitutionPolicy, PolicykitRemoveConstitutionPolicyAdmin)


class PolicykitChangeCommunityDocAdmin(admin.ModelAdmin):
    fields= ('community_doc', 'text',)

    def save_model(self, request, obj, form, change):
        obj.initiator = request.user
        obj.community = request.user.community
        obj.save()

admin_site.register(PolicykitChangeCommunityDoc, PolicykitChangeCommunityDocAdmin)




#
# class ActionAdmin(admin.ModelAdmin):
#     pass
#
# admin_site.register(ActionMeasure, ActionAdmin)
#
# class platformIntegrationAdmin(admin.ModelAdmin):
#     pass
#
# admin_site.register(platformIntegration, platformIntegrationAdmin)
