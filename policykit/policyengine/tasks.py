# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policyengine.models import UserVote, NumberVote, BooleanVote, PlatformAction, PlatformActionBundle, Proposal, PlatformPolicy, CommunityUser, ConstitutionAction, ConstitutionPolicy
from policykit.celery import app
from policyengine.views import *

@shared_task
def consider_proposed_actions():
    def _execute_policy(policy, action):

        if filter_policy(policy, action):
            if not policy.has_notified:
                initialize_policy(policy, action)

                check_result = check_policy(policy, action)
                if check_result == Proposal.PASSED:
                    pass_policy(policy, action)
                elif check_result == Proposal.FAILED:
                    fail_policy(policy, action)
                else:
                    notify_policy(policy, action)
            else:
                check_result = check_policy(policy, action)
                if check_result == Proposal.PASSED:
                    pass_policy(policy, action)
                elif check_result == Proposal.FAILED:
                    fail_policy(policy, action)

    platform_actions = PlatformAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    for action in platform_actions:

        #logger.info(action)

         #if they have execute permission, skip all policies
        if action.initiator.has_perm(action.app_name + '.can_execute_' + action.action_codename):
            action.execute()
        else:
            for policy in PlatformPolicy.objects.filter(community=action.community):
                _execute_policy(policy, action)

    bundle_actions = PlatformActionBundle.objects.filter(proposal__status=Proposal.PROPOSED)
    for action in bundle_actions:
        #if they have execute permission, skip all policies

        if action.initiator.has_perm(action.app_name + '.can_execute_' + action.action_codename):
            action.execute()
        else:
            for policy in PlatformPolicy.objects.filter(community=action.community):
                _execute_policy(policy, action)

    constitution_actions = ConstitutionAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    for action in constitution_actions:
        #if they have execute permission, skip all policies
        if action.initiator.has_perm(action.app_name + '.can_execute_' + action.action_codename):
            action.execute()
        else:
            for policy in ConstitutionPolicy.objects.filter(community=action.community):
                _execute_policy(policy, action)
