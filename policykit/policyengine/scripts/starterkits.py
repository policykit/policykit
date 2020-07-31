from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.govinterface.models import LogEntry
from polymorphic.models import PolymorphicModel
from django.core.exceptions import ValidationError
from policyengine.views import check_policy, filter_policy, initialize_policy, pass_policy, fail_policy, notify_policy
import urllib
import json
from policyengine.models import *

import logging

default_starterkit = StarterKit(name = "Default Starter Kit")
default_starterkit.save()
    
policy1 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Policy: all policies pass",
                                       name = "Starter name",
                                       starterkit = default_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )
        
default_base_role = GenericRole.objects.create(role_name = "Base User", starterkit = default_starterkit, is_base_role = True)
            
default_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']
            
for perm in default_perms:
    p1 = Permission.objects.get(name=perm)
    default_base_role.permissions.add(p1)
