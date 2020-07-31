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

#default starterkit -- all users have ability to view/propose actions + all actions pass automatically
default_starterkit = StarterKit(name = "Default Starter Kit")
default_starterkit.save()
    
policy1 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: all constitution actions pass",
                                       name = "All Constitution Actions Pass",
                                       starterkit = default_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

policy2 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all platform actions pass",
                                       name = "All Platform Actions Pass",
                                       starterkit = default_starterkit,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )
        
default_base_role = GenericRole.objects.create(role_name = "Base User", starterkit = default_starterkit, is_base_role = True,  user_group = "all")
            
default_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add communityactionbundle', 'Can add communitypolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change community policy', 'Can add policykit change constitution policy', 'Can add policykit remove community policy', 'Can add policykit remove constitution policy', 'Can add policykit add community policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']
            
for perm in default_perms:
    p1 = Permission.objects.get(name=perm)
    default_base_role.permissions.add(p1)

#starter kit for standard moderator/user structure
mod_user_starterkit = StarterKit(name = "Mod and User Starter Kit")
mod_user_starterkit.save()

policy1 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = """
                                           if action.initiator.groups.filter(name = "Moderator").exists():
                                               return PASSED
                                           else:
                                               return FAILED
                                           """,
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: constitution actions pass if proposed by moderator",
                                       name = "Starter name",
                                       starterkit = mod_user_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

policy2 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all platform actions pass",
                                       name = "All Platform Actions Pass",
                                       starterkit = mod_user_starterkit,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

mod_user_base_role = GenericRole.objects.create(role_name = "Base User", starterkit = mod_user_starterkit, is_base_role = True, user_group = "nonadmins")

mod_user_mod_role = GenericRole.objects.create(role_name = "Moderator", starterkit = mod_user_starterkit, is_base_role = True, user_group = "admins")

mod_user_base_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add communityactionbundle', 'Can add communitypolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change community policy', 'Can add policykit change constitution policy', 'Can add policykit remove community policy', 'Can add policykit remove constitution policy', 'Can add policykit add community policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

mod_user_mod_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add communityactionbundle', 'Can add communitypolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change community policy', 'Can add policykit change constitution policy', 'Can add policykit remove community policy', 'Can add policykit remove constitution policy', 'Can add policykit add community policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

for perm in mod_user_base_perms:
    p1 = Permission.objects.get(name=perm)
    mod_user_base_role.permissions.add(p1)

for perm in mod_user_mod_perms:
    p1 = Permission.objects.get(name=perm)
    mod_user_mod_role.permissions.add(p1)


#starter kit for basic democracy structure

#need policy for -- voting (when non-moderator proposes action, must be voted on by moderators?)
#need policy for -- spam prevention

democracy_starterkit = StarterKit(name = "Democracy Starter Kit")
democracy_starterkit.save()

policy1 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = """
                                           if action.initiator.groups.filter(name = "Moderator").exists():
                                               return PASSED
                                           else:
                                               return FAILED
                                           """,
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: constitution actions pass if proposed by moderator",
                                       name = "Starter name",
                                       starterkit = democracy_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

policy2 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all policies pass",
                                       name = "Starter name",
                                       starterkit = democracy_starterkit,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

policy1 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = """
                                           if action.initiator.groups.filter(name = "Moderator").exists():
                                           return PASSED
                                           else:
                                           return FAILED
                                           """,
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: constitution actions pass if proposed by moderator",
                                       name = "Starter name",
                                       starterkit = democracy_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

democracy_base_role = GenericRole.objects.create(role_name = "Base User", starterkit = democracy_starterkit, is_base_role = True, user_group = "nonadmins")

democracy_mod_role = GenericRole.objects.create(role_name = "Moderator", starterkit = democracy_starterkit, is_base_role = True, user_group = "admins")

democracy_base_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add communityactionbundle', 'Can add communitypolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change community policy', 'Can add policykit change constitution policy', 'Can add policykit remove community policy', 'Can add policykit remove constitution policy', 'Can add policykit add community policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

democracy_mod_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add communityactionbundle', 'Can add communitypolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change community policy', 'Can add policykit change constitution policy', 'Can add policykit remove community policy', 'Can add policykit remove constitution policy', 'Can add policykit add community policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

for perm in democracy_base_perms:
    p1 = Permission.objects.get(name=perm)
    democracy_base_role.permissions.add(p1)

for perm in democracy_mod_perms:
    p1 = Permission.objects.get(name=perm)
    democracy_mod_role.permissions.add(p1)

#starter kit for benevolent dictator
benev_dictator_starterkit = StarterKit(name = "Democracy Starter Kit")
benev_dictator_starterkit.save()

policy1 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = """
                                           if action.initiator.groups.filter(name = "Benevolent Dictator").exists():
                                               return PASSED
                                           else:
                                               return FAILED
                                           """,
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: only actions proposed by dictator pass",
                                       name = "Starter name",
                                       starterkit = benev_dictator_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

policy2 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all platform actions pass",
                                       name = "All Platform Actions Pass",
                                       starterkit = benev_dictator_starterkit,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

benev_dictator_base_role = GenericRole.objects.create(role_name = "Base User", starterkit = democracy_starterkit, is_base_role = True, user_group = "all")

benev_dictator_dictator_role = GenericRole.objects.create(role_name = "Benevolent Dictator", starterkit = democracy_starterkit, is_base_role = True, user_group = "creator")


benev_dictator_base_perms = ['Can view boolean vote', 'Can view number vote', 'Can view communityactionbundle', 'Can view communitypolicybundle', 'Can view constitutionactionbundle', 'Can view constitutionpolicybundle', 'Can view policykit add role', 'Can view policykit delete role', 'Can view policykit add permission', 'Can view policykit remove permission', 'Can view policykit add user role', 'Can view policykit remove user role', 'Can view policykit change community policy', 'Can view policykit change constitution policy', 'Can view policykit remove community policy', 'Can view policykit remove constitution policy', 'Can view policykit add community policy', 'Can view policykit add constitution policy', 'Can view policykit change community doc']

benev_dictator_dictator_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add communityactionbundle', 'Can add communitypolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change community policy', 'Can add policykit change constitution policy', 'Can add policykit remove community policy', 'Can add policykit remove constitution policy', 'Can add policykit add community policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

for perm in benev_dictator_base_perms:
    p1 = Permission.objects.get(name=perm)
    benev_dictator_base_role.permissions.add(p1)

