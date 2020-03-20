# encoding: utf-8
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from jet.dashboard import modules
from jet.dashboard.dashboard import Dashboard, AppIndexDashboard
from jet.utils import get_admin_site_name
from policykit.dashboard_modules import PolicyModule

import logging


logger = logging.getLogger(__name__)

class CustomIndexDashboard(Dashboard):
    columns = 3
    

    def init_with_context(self, context):
        
        self.available_children.append(modules.LinkList)
        self.available_children.append(modules.AppList)

        # append an app list module for "Applications"
        self.children.append(modules.AppList(
            _('Applications'),
            exclude=('auth.*',),
            column=0,
            order=0,
            deletable=False,
        ))
        
        
        self.children.append(PolicyModule(
            policy_type="Process",
            status="passed",
            title="Passed Process Policies",
            deletable=False,
            column=1,
            order=0,
        ))
        
        self.children.append(PolicyModule(
            policy_type="Process",
            status="proposed",
            title="Proposed Process Policies",
            deletable=False,
            column=1,
            order=1,
        ))
        
        self.children.append(PolicyModule(
            policy_type="Community",
            status="passed",
            title="Passed Community Policies",
            deletable=False,
            column=1,
            order=2,
        ))
        
        self.children.append(PolicyModule(
            policy_type="Community",
            status="proposed",
            title="Proposed Community Policies",
            deletable=False,
            column=1,
            order=3,
        ))
        

        # append an app list module for "Administration"
        self.children.append(modules.AppList(
            _('Administration'),
            models=('auth.*',),
            column=2,
            order=0,
            deletable=False,
        ))

        # append a recent actions module
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            10,
            column=2,
            order=1,
            deletable=False,
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