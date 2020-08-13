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
from redditintegration.models import RedditStarterKit
from slackintegration.models import SlackStarterKit

import logging

#default starterkit -- all users have ability to view/propose actions + all actions pass automatically
testing_starterkit_slack = SlackStarterKit(name = "Testing Starter Kit")
testing_starterkit_slack.save()

testing_starterkit_reddit = RedditStarterKit(name = "Testing Starter Kit")
testing_starterkit_reddit.save()
    
testing_policy1_slack = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: all constitution actions pass automatically",
                                       name = "All Constitution Actions Pass",
                                       starterkit = testing_starterkit_slack,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

testing_policy2_slack = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all platform actions pass automatically",
                                       name = "All Platform Actions Pass",
                                       starterkit = testing_starterkit_slack,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

testing_policy1_reddit = GenericPolicy.objects.create(filter = "return True",
                                                     initialize = "pass",
                                                     check = "return PASSED",
                                                     notify = "pass",
                                                     success = "action.execute()",
                                                     fail = "pass",
                                                     description = "Starter Constitution Policy: all constitution actions pass automatically",
                                                     name = "All Constitution Actions Pass",
                                                     starterkit = testing_starterkit_reddit,
                                                     is_constitution = True,
                                                     is_bundled = False,
                                                     has_notified = False,
                                                     )

testing_policy2_reddit = GenericPolicy.objects.create(filter = "return True",
                                                     initialize = "pass",
                                                     check = "return PASSED",
                                                     notify = "pass",
                                                     success = "action.execute()",
                                                     fail = "pass",
                                                     description = "Starter Platform Policy: all platform actions pass automatically",
                                                     name = "All Platform Actions Pass",
                                                     starterkit = testing_starterkit_reddit,
                                                     is_constitution = False,
                                                     is_bundled = False,
                                                     has_notified = False,
                                                     )
        
testing_base_role_slack = GenericRole.objects.create(role_name = "Testing: Base User", name = "Testing: Base User (Slack)", starterkit = testing_starterkit_slack, is_base_role = True, user_group = "all")

testing_base_role_reddit = GenericRole.objects.create(role_name = "Testing: Base User", name = "Testing: Base User (Reddit)", starterkit = testing_starterkit_reddit, is_base_role = True, user_group = "all")
            
testing_const_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

testing_base_role_slack.plat_perm_set = json.dumps(['view', 'propose'])
testing_base_role_slack.save()

testing_base_role_reddit.plat_perm_set = json.dumps(['view', 'propose'])
testing_base_role_reddit.save()

for perm in testing_const_perms:
    p1 = Permission.objects.get(name=perm)
    testing_base_role_slack.permissions.add(p1)
    testing_base_role_reddit.permissions.add(p1)

#starter kit for standard moderator/user structure
admin_user_starterkit_slack = SlackStarterKit(name = "Admin and User Starter Kit")
admin_user_starterkit_slack.save()

admin_user_starterkit_reddit = RedditStarterKit(name = "Admin and User Starter Kit")
admin_user_starterkit_reddit.save()

admin_user_policy1_slack = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = """
if action.initiator.groups.filter(name = "Administrator").exists():
    return PASSED
else:
    return FAILED
                                       """,
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: constitution actions pass if proposed by moderator",
                                       name = "Admin and User: All Constitution Actions from Moderators Pass",
                                       starterkit = admin_user_starterkit_slack,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

admin_user_policy2_slack = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all platform actions pass",
                                       name = "Admin and User: All Platform Actions Pass",
                                       starterkit = admin_user_starterkit_slack,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

admin_user_policy1_reddit = GenericPolicy.objects.create(filter = "return True",
                                                  initialize = "pass",
                                                  check = """
if action.initiator.groups.filter(name = "Administrator").exists():
    return PASSED
else:
    return FAILED
                                                      """,
                                                  notify = "pass",
                                                  success = "action.execute()",
                                                  fail = "pass",
                                                  description = "Starter Constitution Policy: constitution actions pass if proposed by moderator",
                                                  name = "Admin and User: All Constitution Actions from Moderators Pass",
                                                  starterkit = admin_user_starterkit_reddit,
                                                  is_constitution = True,
                                                  is_bundled = False,
                                                  has_notified = False,
                                                  )

admin_user_policy2_reddit = GenericPolicy.objects.create(filter = "return True",
                                                  initialize = "pass",
                                                  check = "return PASSED",
                                                  notify = "pass",
                                                  success = "action.execute()",
                                                  fail = "pass",
                                                  description = "Starter Platform Policy: all platform actions pass",
                                                  name = "Admin and User: All Platform Actions Pass",
                                                  starterkit = admin_user_starterkit_reddit,
                                                  is_constitution = False,
                                                  is_bundled = False,
                                                  has_notified = False,
                                                  )

admin_user_base_role_slack = GenericRole.objects.create(role_name = "Admin and User: Base User", name = "Admin and User: Base User (Slack)", starterkit = admin_user_starterkit_slack, is_base_role = True, user_group = "nonadmins")

admin_user_base_role_reddit = GenericRole.objects.create(role_name = "Admin and User: Base User", name = "Admin and User: Base User (Reddit)", starterkit = admin_user_starterkit_reddit, is_base_role = True, user_group = "nonadmins")

admin_user_mod_role_slack = GenericRole.objects.create(role_name = "Administrator", name = "Administrator (Slack)", starterkit = admin_user_starterkit_slack, is_base_role = False, user_group = "admins")

admin_user_mod_role_reddit = GenericRole.objects.create(role_name = "Administrator", name = "Administrator (Reddit)", starterkit = admin_user_starterkit_reddit, is_base_role = False, user_group = "admins")

admin_user_base_const_perms = ['Can view boolean vote', 'Can view number vote', 'Can view platformactionbundle', 'Can view platformpolicybundle', 'Can view constitutionactionbundle', 'Can view constitutionpolicybundle', 'Can view policykit add role', 'Can view policykit delete role', 'Can view policykit add permission', 'Can view policykit remove permission', 'Can view policykit add user role', 'Can view policykit remove user role', 'Can view policykit change platform policy', 'Can view policykit change constitution policy', 'Can view policykit remove platform policy', 'Can view policykit remove constitution policy', 'Can view policykit add platform policy', 'Can view policykit add constitution policy', 'Can view policykit change community doc']

admin_user_base_role_slack.plat_perm_set = json.dumps(['view'])
admin_user_base_role_slack.save()

admin_user_base_role_reddit.plat_perm_set = json.dumps(['view'])
admin_user_base_role_reddit.save()

admin_user_mod_const_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

admin_user_mod_role_slack.plat_perm_set = json.dumps(['view', 'propose'])
admin_user_mod_role_slack.save()

admin_user_mod_role_reddit.plat_perm_set = json.dumps(['view', 'propose'])
admin_user_mod_role_reddit.save()

for perm in admin_user_base_const_perms:
    p1 = Permission.objects.get(name=perm)
    admin_user_base_role_slack.permissions.add(p1)
    admin_user_base_role_reddit.permissions.add(p1)

for perm in admin_user_mod_const_perms:
    p1 = Permission.objects.get(name=perm)
    admin_user_mod_role_slack.permissions.add(p1)
    admin_user_base_role_reddit.permissions.add(p1)

#starter kit for basic democracy structure

democracy_starterkit_slack = SlackStarterKit(name = "Democracy Starter Kit")
democracy_starterkit_slack.save()

democracy_starterkit_reddit = RedditStarterKit(name = "Democracy Starter Kit")
democracy_starterkit_reddit.save()

democracy_policy1_slack = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all platform actions pass automatically",
                                       name = "Democracy: All Platform Actions Pass",
                                       starterkit = democracy_starterkit_slack,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

democracy_policy2_slack = GenericPolicy.objects.create(
                                       filter = """
                                           if not action.initiator.groups.filter(name = "Moderator").exists():
                                               return True
                                           else:
                                               return False
                                           """,
                                       initialize = "pass",
                                       check = """
import math
                                           
voter_users = users.filter(groups__name__in=['Democracy: Voter'])
yes_votes = action.proposal.get_yes_votes(users=voter_users, value=True)
if len(yes_votes) >= math.ceil(voter_users.count()/2):
    return PASSED
elif action.proposal.time_elapsed() > datetime.timedelta(days=1):
    return FAILED
                                           """,
                                       notify = """
voter_users = users.filter(groups__name__in=['Democracy: Voter'])
action.platform.notify_users(action, policy, users=voter_users, text='Please vote')
                                           """,
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: all constitution actions must be approved by voters in voting process",
                                       name = "Democracy: Constitution Actions Voted In",
                                       starterkit = democracy_starterkit_slack,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

democracy_policy1_reddit = GenericPolicy.objects.create(filter = "return True",
                                                       initialize = "pass",
                                                       check = "return PASSED",
                                                       notify = "pass",
                                                       success = "action.execute()",
                                                       fail = "pass",
                                                       description = "Starter Platform Policy: all platform actions pass automatically",
                                                       name = "Democracy: All Platform Actions Pass",
                                                       starterkit = democracy_starterkit_reddit,
                                                       is_constitution = False,
                                                       is_bundled = False,
                                                       has_notified = False,
                                                       )

democracy_policy2_reddit = GenericPolicy.objects.create(
                                                       filter = """
if not action.initiator.groups.filter(name = "Moderator").exists():
    return True
else:
    return False
                                                           """,
                                                       initialize = "pass",
                                                       check = """
import math

voter_users = users.filter(groups__name__in=['Democracy: Voter'])
yes_votes = action.proposal.get_yes_votes(users=voter_users, value=True)
if len(yes_votes) >= math.ceil(voter_users.count()/2):
   return PASSED
elif action.proposal.time_elapsed() > datetime.timedelta(days=1):
   return FAILED
                                                           """,
                                                       notify = """
voter_users = users.filter(groups__name__in=['Democracy: Voter'])
action.platform.notify_users(action, policy, users=voter_users, text='Please vote')
                                                           """,
                                                       success = "action.execute()",
                                                       fail = "pass",
                                                       description = "Starter Constitution Policy: all constitution actions must be approved by voters in voting process",
                                                       name = "Democracy: Constitution Actions Voted In",
                                                       starterkit = democracy_starterkit_reddit,
                                                       is_constitution = True,
                                                       is_bundled = False,
                                                       has_notified = False,
                                                       )

democracy_base_role_slack = GenericRole.objects.create(role_name = "Democracy: Base User", name = "Democracy: Base User (Slack)", starterkit = democracy_starterkit_slack, is_base_role = True, user_group = "nonadmins")

democracy_base_role_reddit = GenericRole.objects.create(role_name = "Democracy: Base User", name = "Democracy: Base User (Reddit)", starterkit = democracy_starterkit_reddit, is_base_role = True, user_group = "nonadmins")

democracy_voter_role_slack = GenericRole.objects.create(role_name = "Democracy: Voter", name = "Democracy: Voter (Slack)", starterkit = democracy_starterkit_slack, is_base_role = False, user_group = "admins")

democracy_voter_role_reddit = GenericRole.objects.create(role_name = "Democracy: Voter", name = "Democracy: Voter (Reddit)", starterkit = democracy_starterkit_reddit, is_base_role = False, user_group = "admins")

democracy_base_const_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

democracy_base_role_slack.plat_perm_set = json.dumps(['view', 'propose'])
democracy_base_role_slack.save()

democracy_base_role_reddit.plat_perm_set = json.dumps(['view', 'propose'])
democracy_base_role_reddit.save()

democracy_voter_const_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

democracy_voter_role_slack.plat_perm_set = json.dumps(['view', 'propose'])
democracy_voter_role_slack.save()

democracy_voter_role_reddit.plat_perm_set = json.dumps(['view', 'propose'])
democracy_voter_role_reddit.save()

for perm in democracy_base_const_perms:
    p1 = Permission.objects.get(name=perm)
    democracy_base_role_slack.permissions.add(p1)
    democracy_base_role_reddit.permissions.add(p1)

for perm in democracy_voter_const_perms:
    p1 = Permission.objects.get(name=perm)
    democracy_voter_role_slack.permissions.add(p1)
    democracy_base_role_reddit.permissions.add(p1)

#starter kit for dictator
dictator_starterkit_slack = SlackStarterKit(name = "Dictator Starter Kit")
dictator_starterkit_slack.save()

dictator_starterkit_reddit = RedditStarterKit(name = "Dictator Starter Kit")
dictator_starterkit_reddit.save()

dictator_policy1_slack = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return FAILED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: only actions proposed by dictator pass",
                                       name = "Benevolent Dictator: Only Benevolent Dictator's Constitution Actions Pass",
                                       starterkit = dictator_starterkit_slack,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

dictator_policy2_slack = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Platform Policy: all platform actions pass",
                                       name = "Benevolent Dictator: All Platform Actions Pass",
                                       starterkit = dictator_starterkit_slack,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

dictator_policy1_reddit = GenericPolicy.objects.create(filter = "return True",
                                                initialize = "pass",
                                                check = "return FAILED",
                                                notify = "pass",
                                                success = "action.execute()",
                                                fail = "pass",
                                                description = "Starter Constitution Policy: only actions proposed by dictator pass",
                                                name = "Benevolent Dictator: Only Benevolent Dictator's Constitution Actions Pass",
                                                starterkit = dictator_starterkit_reddit,
                                                is_constitution = True,
                                                is_bundled = False,
                                                has_notified = False,
                                                )

dictator_policy2_reddit = GenericPolicy.objects.create(filter = "return True",
                                                initialize = "pass",
                                                check = "return PASSED",
                                                notify = "pass",
                                                success = "action.execute()",
                                                fail = "pass",
                                                description = "Starter Platform Policy: all platform actions pass",
                                                name = "Benevolent Dictator: All Platform Actions Pass",
                                                starterkit = dictator_starterkit_reddit,
                                                is_constitution = False,
                                                is_bundled = False,
                                                has_notified = False,
                                                )

dictator_base_role_slack = GenericRole.objects.create(role_name = "Dictator: Base User", name = "Dictator: Base User (Slack)", starterkit = dictator_starterkit_slack, is_base_role = True, user_group = "all")

dictator_base_role_reddit = GenericRole.objects.create(role_name = "Dictator: Base User", name = "Dictator: Base User (Reddit)", starterkit = dictator_starterkit_slack, is_base_role = True, user_group = "all")

dictator_dictator_role_slack = GenericRole.objects.create(role_name = "Dictator", name = "Dictator (Slack)", starterkit = dictator_starterkit_slack, is_base_role = False, user_group = "creator")

dictator_dictator_role_reddit = GenericRole.objects.create(role_name = "Dictator", name = "Dictator (Reddit)", starterkit = dictator_starterkit_reddit, is_base_role = False, user_group = "creator")

dictator_base_const_perms = ['Can view boolean vote', 'Can view number vote', 'Can view platformactionbundle', 'Can view platformpolicybundle', 'Can view constitutionactionbundle', 'Can view constitutionpolicybundle', 'Can view policykit add role', 'Can view policykit delete role', 'Can view policykit add permission', 'Can view policykit remove permission', 'Can view policykit add user role', 'Can view policykit remove user role', 'Can view policykit change platform policy', 'Can view policykit change constitution policy', 'Can view policykit remove platform policy', 'Can view policykit remove constitution policy', 'Can view policykit add platform policy', 'Can view policykit add constitution policy', 'Can view policykit change community doc']

dictator_base_role_slack.plat_perm_set = json.dumps(['view', 'propose'])
dictator_base_role_slack.save()

dictator_base_role_reddit.plat_perm_set = json.dumps(['view', 'propose'])
dictator_base_role_reddit.save()

dictator_dictator_const_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc', 'Can execute policykit add role', 'Can execute policykit delete role', 'Can execute policykit add permission', 'Can execute policykit remove permission', 'Can execute policykit add user role', 'Can execute policykit remove user role', 'Can execute policykit change platform policy', 'Can execute policykit change constitution policy', 'Can execute policykit remove platform policy', 'Can execute policykit remove constitution policy', 'Can execute policykit add platform policy', 'Can execute policykit add constitution policy', 'Can execute policykit change community doc']

dictator_dictator_role_slack.plat_perm_set = json.dumps(['view', 'propose', 'execute'])
dictator_dictator_role_slack.save()

dictator_dictator_role_reddit.plat_perm_set = json.dumps(['view', 'propose', 'execute'])
dictator_dictator_role_reddit.save()

for perm in dictator_base_const_perms:
    p1 = Permission.objects.get(name=perm)
    dictator_base_role_slack.permissions.add(p1)
    dictator_base_role_reddit.permissions.add(p1)

for perm in dictator_dictator_const_perms:
    p1 = Permission.objects.get(name=perm)
    dictator_dictator_role_slack.permissions.add(p1)
    dictator_base_role_reddit.permissions.add(p1)

#starter kit for jury
jury_starterkit_slack = SlackStarterKit(name = "Jury Starter Kit")
jury_starterkit_slack.save()

jury_starterkit_reddit = RedditStarterKit(name = "Jury Starter Kit")
jury_starterkit_reddit.save()

jury_policy1_slack = GenericPolicy.objects.create(filter = "return True",
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
action.platform.notify_users(action, policy, users=jury_users, text='Please deliberate amongst yourselves before voting')
                                           """,
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: constitutions actions by non-moderator must be passed by random jury of 3 members",
                                       name = "Jury: Constitution Actions Passed by Jury",
                                       starterkit = jury_starterkit_slack,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

jury_policy2_slack = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Jury: Starter Platform Policy: all platform actions pass",
                                       name = "All Platform Actions Pass",
                                       starterkit = jury_starterkit_slack,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

jury_policy1_reddit = GenericPolicy.objects.create(filter = "return True",
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
action.platform.notify_users(action, policy, users=jury_users, text='Please deliberate amongst yourselves before voting')
                                           """,
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Starter Constitution Policy: constitutions actions by non-moderator must be passed by random jury of 3 members",
                                       name = "Jury: Constitution Actions Passed by Jury",
                                       starterkit = jury_starterkit_reddit,
                                       is_constitution = True,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

jury_policy2_reddit = GenericPolicy.objects.create(filter = "return True",
                                       initialize = "pass",
                                       check = "return PASSED",
                                       notify = "pass",
                                       success = "action.execute()",
                                       fail = "pass",
                                       description = "Jury: Starter Platform Policy: all platform actions pass",
                                       name = "All Platform Actions Pass",
                                       starterkit = jury_starterkit_reddit,
                                       is_constitution = False,
                                       is_bundled = False,
                                       has_notified = False,
                                       )

jury_base_role_slack = GenericRole.objects.create(role_name = "Jury: Base User", name = "Jury: Base User (Slack)", starterkit = jury_starterkit_slack, is_base_role = True, user_group = "all")

jury_base_role_reddit = GenericRole.objects.create(role_name = "Jury: Base User", name = "Jury: Base User (Reddit)", starterkit = jury_starterkit_reddit, is_base_role = True, user_group = "all")

jury_base_const_perms = ['Can add boolean vote', 'Can change boolean vote', 'Can delete boolean vote', 'Can view boolean vote', 'Can add number vote', 'Can change number vote', 'Can delete number vote', 'Can view number vote', 'Can add platformactionbundle', 'Can add platformpolicybundle', 'Can add constitutionactionbundle', 'Can add constitutionpolicybundle', 'Can add policykit add role', 'Can add policykit delete role', 'Can add policykit add permission', 'Can add policykit remove permission', 'Can add policykit add user role', 'Can add policykit remove user role', 'Can add policykit change platform policy', 'Can add policykit change constitution policy', 'Can add policykit remove platform policy', 'Can add policykit remove constitution policy', 'Can add policykit add platform policy', 'Can add policykit add constitution policy', 'Can add policykit change community doc']

jury_base_role_slack.plat_perm_set = json.dumps(['view', 'propose'])
jury_base_role_slack.save()

jury_base_role_reddit.plat_perm_set = json.dumps(['view', 'propose'])
jury_base_role_reddit.save()

for perm in jury_base_const_perms:
    p1 = Permission.objects.get(name=perm)
    jury_base_role_slack.permissions.add(p1)
    jury_base_role_reddit.permissions.add(p1)
