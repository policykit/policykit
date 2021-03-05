# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policyengine.models import UserVote, NumberVote, BooleanVote, PlatformAction, PlatformActionBundle, Proposal, PlatformPolicy, CommunityUser, ConstitutionAction, ConstitutionPolicy, execute_policy
from policykit.celery import app
from policyengine.views import *

@shared_task
def consider_proposed_actions():

    platform_actions = PlatformAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    for action in platform_actions:
         #if they have execute permission, skip all policies
        if action.initiator.has_perm(action.app_name + '.can_execute_' + action.action_codename):
            action.execute()
        else:
            for policy in PlatformPolicy.objects.filter(community=action.community):
                execute_policy(policy, action)

    """bundle_actions = PlatformActionBundle.objects.filter(proposal__status=Proposal.PROPOSED)
    for action in bundle_actions:
        #if they have execute permission, skip all policies

        if action.initiator.has_perm(action.app_name + '.can_execute_' + action.action_codename):
            action.execute()
        else:
            for policy in PlatformPolicy.objects.filter(community=action.community):
                execute_policy(policy, action)"""

    constitution_actions = ConstitutionAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    for action in constitution_actions:
        #if they have execute permission, skip all policies
        if action.initiator.has_perm(action.app_name + '.can_execute_' + action.action_codename):
            action.execute()
        else:
            for policy in ConstitutionPolicy.objects.filter(community=action.community):
                execute_policy(policy, action)
