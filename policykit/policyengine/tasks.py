# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policyengine.models import UserVote, NumberVote, BooleanVote, CommunityAction, CommunityActionBundle, Proposal, CommunityPolicy, CommunityUser, ConstitutionAction, ConstitutionPolicy
from policykit.celery import app
from policyengine.views import *

@shared_task
def consider_proposed_actions():

    def _execute_policy(policy, action):

        if filter_policy(policy, action):
            if not policy.has_notified:
                initialize_policy(policy, action)

                cond_result = check_policy(policy, action)
                if cond_result == Proposal.PASSED:
                    pass_policy(policy, action)
                elif cond_result == Proposal.FAILED:
                    fail_policy(policy, action)
                else:
                    notify_policy(policy, action)
            else:
                cond_result = check_policy(policy, action)
                if cond_result == Proposal.PASSED:
                    pass_policy(policy, action)
                elif cond_result == Proposal.FAILED:
                    fail_policy(policy, action)


    community_actions = CommunityAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    for action in community_actions:

        logger.info(action)

        for policy in CommunityPolicy.objects.filter(community=action.community):
            _execute_policy(policy, action)

    bundle_actions = CommunityActionBundle.objects.filter(proposal__status=Proposal.PROPOSED)
    for action in bundle_actions:
        for policy in CommunityPolicy.objects.filter(community=action.community):
            _execute_policy(policy, action)

    constitution_actions = ConstitutionAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    for action in constitution_actions:
        for policy in ConstitutionPolicy.objects.filter(community=action.community):
            _execute_policy(policy, action)
