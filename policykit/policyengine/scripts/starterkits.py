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
        
default_base_role = GenericRole.objects.create(role_name = "Base User", name = "Base User", starterkit = default_starterkit, is_base_role = True, user_group = "all")
            
default_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']
            
for perm in default_perms:
    p1 = Permission.objects.get(name=perm)
    default_base_role.permissions.add(p1)

#starter kit for standard moderator/user structure
mod_user_starterkit = StarterKit(name = "Mod and User Starter Kit")
mod_user_starterkit.save()

mod_user_policy1 = GenericPolicy.objects.create(filter = "return True",
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
                                       name = "Mod/User: All Constitution Actions from Moderators Pass",
                                       starterkit = mod_user_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

mod_user_policy2 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all platform actions pass",
                                       name = "Mod/User: All Platform Actions Pass",
                                       starterkit = mod_user_starterkit,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

mod_user_base_role = GenericRole.objects.create(role_name = "Mod/User: Base User", name = "Mod/User: Base User", starterkit = mod_user_starterkit, is_base_role = True, user_group = "nonadmins")

mod_user_mod_role = GenericRole.objects.create(role_name = "Moderator", name = "Moderator", starterkit = mod_user_starterkit, is_base_role = False, user_group = "admins")

mod_user_base_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

mod_user_mod_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

for perm in mod_user_base_perms:
    p1 = Permission.objects.get(name=perm)
    mod_user_base_role.permissions.add(p1)

for perm in mod_user_mod_perms:
    p1 = Permission.objects.get(name=perm)
    mod_user_mod_role.permissions.add(p1)


#starter kit for basic democracy structure

#need policy for -- voting (when non-moderator proposes action, must be voted on by moderators?)

democracy_starterkit = StarterKit(name = "Democracy Starter Kit")
democracy_starterkit.save()

democracy_policy1 = GenericPolicy.objects.create(filter = "return True",
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
                                       name = "Democracy: All Constitution Actions from Moderators Pass",
                                       starterkit = democracy_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

democracy_policy2 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all policies pass",
                                       name = "Democracy: All Platform Actions Pass",
                                       starterkit = democracy_starterkit,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

democracy_policy3 = GenericPolicy.objects.create(
                                       filter = """
                                           if not action.initiator.groups.filter(name = "Moderator").exists():
                                               return True
                                           else:
                                               return False
                                           """,
                                       initialize = "pass",
                                       check = """
import math
                                           
voter_users = users.filter(groups__name__in=['Moderator'])
yes_votes = action.proposal.get_yes_votes(users=voter_users, value=True)
if len(yes_votes) >= math.ceil(voter_users.count()/2):
    return PASSED
elif action.proposal.time_elapsed() > datetime.timedelta(days=1):
    return FAILED
                                           """,
                                       notify = """
voter_users = users.filter(groups__name__in=['Moderator'])
action.platform.notify_users(action, policy, users=voter_users,
                                           """,
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: all constitution actions must be approved by moderators in voting process",
                                       name = "Democracy: Constitution Actions must be approved by Moderators",
                                       starterkit = democracy_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

democracy_base_role = GenericRole.objects.create(role_name = "Democracy: Base User", name = "Democracy: Base User", starterkit = democracy_starterkit, is_base_role = True, user_group = "nonadmins")

democracy_mod_role = GenericRole.objects.create(role_name = "Democracy: Moderator", name = "Democracy: Moderator", starterkit = democracy_starterkit, is_base_role = False, user_group = "admins")

democracy_base_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

democracy_mod_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

for perm in democracy_base_perms:
    p1 = Permission.objects.get(name=perm)
    democracy_base_role.permissions.add(p1)

for perm in democracy_mod_perms:
    p1 = Permission.objects.get(name=perm)
    democracy_mod_role.permissions.add(p1)

#starter kit for benevolent dictator
benev_dictator_starterkit = StarterKit(name = "Benevolent Dictator Starter Kit")
benev_dictator_starterkit.save()

benev_policy1 = GenericPolicy.objects.create(filter = "return True",
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
                                       name = "Benevolent Dictator: Only Benevolent Dictator's Constitution Actions Pass",
                                       starterkit = benev_dictator_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

benev_policy2 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all platform actions pass",
                                       name = "Benevolent Dictator: All Platform Actions Pass",
                                       starterkit = benev_dictator_starterkit,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

benev_dictator_base_role = GenericRole.objects.create(role_name = "Benevolent Dictator: Base User", name = "Benevolent Dictator: Base User", starterkit = benev_dictator_starterkit, is_base_role = True, user_group = "all")

benev_dictator_dictator_role = GenericRole.objects.create(role_name = "Benevolent Dictator", name = "Benevolent Dictator", starterkit = benev_dictator_starterkit, is_base_role = False, user_group = "creator")

benev_dictator_base_perms = ['Can view boolean vote', 'Can view number vote', 'Can view platformactionbundle', 'Can view platformpolicybundle', 'Can view constitutionactionbundle', 'Can view constitutionpolicybundle', 'Can view policykit add role', 'Can view policykit delete role', 'Can view policykit add permission', 'Can view policykit remove permission', 'Can view policykit add user role', 'Can view policykit remove user role', 'Can view policykit change platform policy', 'Can view policykit change constitution policy', 'Can view policykit remove platform policy', 'Can view policykit remove constitution policy', 'Can view policykit add platform policy', 'Can view policykit add constitution policy', 'Can view policykit change community doc']

benev_dictator_dictator_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

for perm in benev_dictator_base_perms:
    p1 = Permission.objects.get(name=perm)
    benev_dictator_base_role.permissions.add(p1)

for perm in benev_dictator_dictator_perms:
    p1 = Permission.objects.get(name=perm)
    benev_dictator_dictator_role.permissions.add(p1)

#starter kit for jury
jury_starterkit = StarterKit(name = "Jury Starter Kit")
jury_starterkit.save()

jury_policy1 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = """
usernames = [u.username for u in users]
jury = random.sample(usernames, k=3)
action.data.add('jury', jury)
                                           """,
                                       check = """
jury = action.data.get('jury')
jury_users = users.filter(username__in=jury)
yes_votes = action.proposal.get_yes_votes(users=jury_users, value=True)
if len(yes_votes) >= 2:
   return PASSED
elif action.proposal.time_elapsed() > datetime.timedelta(days=2):
   return FAILED
                                           """,
                                       notify = """
jury = action.data.get('jury')
jury_users = users.filter(username__in=jury)
action.platform.notify_users(action, policy, users=jury_users,
                                           """,
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: constitutions actions by non-moderator must be passed by random jury of 3 members",
                                       name = "Jury: Only Actions Passed by Jury Pass",
                                       starterkit = jury_starterkit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

jury_policy2 = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Jury: Starter Platform Policy: all platform actions pass",
                                       name = "All Platform Actions Pass",
                                       starterkit = jury_starterkit,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

    #jury_policy3 = GenericPolicy.objects.create(filter = "return True",
    #                                       initialize = "pass",
    #                                  check = """
    #                                      if action.initiator.groups.filter(name = "Moderator").exists():
    #                                      return PASSED
    #                                       else:
    #                                       return FAILED
    #                                       """,
    #                                   notify = "pass",
    #                                   success = "action.execute()",
    #                                   fail = "pass",
    #                                   description = "Starter Constitution Policy: constitution actions pass if proposed by moderator",
    #                                   name = "All Constitution Actions from Moderators Pass",
    #                                   starterkit = jury_starterkit,
    #                                   is_constitution = True,
    #                                   is_bundled = False,
    #                                   has_notified = False,
    #                                   )

jury_base_role = GenericRole.objects.create(role_name = "Jury: Base User", name = "Jury: Base User", starterkit = jury_starterkit, is_base_role = True, user_group = "all")

jury_base_perms = ['Can view boolean vote', 'Can view number vote', 'Can view platformactionbundle', 'Can view platformpolicybundle', 'Can view constitutionactionbundle', 'Can view constitutionpolicybundle', 'Can view policykit add role', 'Can view policykit delete role', 'Can view policykit add permission', 'Can view policykit remove permission', 'Can view policykit add user role', 'Can view policykit remove user role', 'Can view policykit change platform policy', 'Can view policykit change constitution policy', 'Can view policykit remove platform policy', 'Can view policykit remove constitution policy', 'Can view policykit add platform policy', 'Can view policykit add constitution policy', 'Can view policykit change community doc']

for perm in jury_base_perms:
    p1 = Permission.objects.get(name=perm)
    jury_base_role.permissions.add(p1)

