# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policyengine.models import UserVote, CommunityAction, Proposal, CommunityPolicy, CommunityUser
from policykit.celery import app
from policyengine.views import *

@shared_task
def consider_proposed_actions():
    proposed_actions = CommunityAction.objects.filter(proposal__status=Proposal.PROPOSED)
    for action in proposed_actions:
        for policy in CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=action.community_integration):
            if check_filter_code(policy, action):
                cond_result = check_policy_code(policy)
                if cond_result == Proposal.PASSED:
                    exec(policy.policy_action_code)
                elif cond_result == Proposal.FAILED:
                    exec(policy.policy_failure_code)

