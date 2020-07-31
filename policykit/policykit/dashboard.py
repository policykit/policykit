# encoding: utf-8
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from jet.dashboard import modules
from jet.dashboard.dashboard import Dashboard, AppIndexDashboard
from jet.utils import get_admin_site_name
from policykit.dashboard_modules import PolicyModule, RolePermissionModule

import logging


logger = logging.getLogger(__name__)

class CustomIndexDashboard(Dashboard):
    columns = 3
    

    def init_with_context(self, context):
        
        # append an app list module for "Applications"
        self.children.append(modules.AppList(
            _('Applications'),
            exclude=('auth.*',),
            column=0,
            order=0,
            deletable=False,
            draggable=False,
        ))
        
        
        self.children.append(PolicyModule(
            policy_type="Constitution",
            title="Passed Constitution Policies",
            deletable=False,
            contrast=True,
            draggable=False,
            column=1,
            order=0,
        ))
        
        self.children.append(PolicyModule(
            policy_type="Platform",
            title="Passed Platform Policies",
            deletable=False,
            contrast=True,
            draggable=False,
            column=1,
            order=2,
        ))
        
        self.children.append(RolePermissionModule(
            deletable=False,
            contrast=True,
            draggable=False,
            column=2,
            order=0,
        ))
        


        # append a recent actions module
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            10,
            column=2,
            order=1,
            deletable=False,
            draggable=False,
        ))
        
        
        site_name = get_admin_site_name(context)
        # append a link list module for "quick links"
        self.children.append(modules.LinkList(
            _('Quick links'),
            layout='inline',
            draggable=False,
            deletable=False,
            collapsible=False,
            children=[
                [_('Return to site'), '/'],
                [_('Change password'),
                 reverse('%s:password_change' % site_name)],
                [_('Log out'), reverse('%s:logout' % site_name)],
            ],
            column=2,
            order=2
        ))

        



class CustomAppIndexDashboard(AppIndexDashboard):
    def init_with_context(self, context):
        self.available_children.append(modules.LinkList)

        self.children.append(modules.ModelList(
            title=_('Application models'),
            models=self.models(),
            column=0,
            order=0
        ))
        self.children.append(modules.RecentActions(
            include_list=self.get_app_content_types(),
            column=1,
            order=0
        ))
