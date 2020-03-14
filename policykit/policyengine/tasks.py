# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policyengine.models import UserVote, NumberVote, BooleanVote, CommunityAction, CommunityActionBundle, Proposal, CommunityPolicy, CommunityUser
from policykit.celery import app
from policyengine.views import *

@shared_task
def consider_proposed_actions():
    
    def _execute_policy(policy, action):
        if check_filter_code(policy, action):
            
            if not policy.has_notified:
                initialize_code(policy, action)
                
                cond_result = check_policy_code(policy, action)
                if cond_result == Proposal.PASSED:
                    exec(policy.policy_action_code)
                elif cond_result == Proposal.FAILED:
                    exec(policy.policy_failure_code)
                else:
                    exec(policy.policy_notify_code)
            else:
                cond_result = check_policy_code(policy, action)
                if cond_result == Proposal.PASSED:
                    exec(policy.policy_action_code)
                elif cond_result == Proposal.FAILED:
                    exec(policy.policy_failure_code)
        
    
    community_actions = CommunityAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    for action in community_actions:
        for policy in CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=action.community_integration):
            _execute_policy(policy, action)
            
    bundle_actions = CommunityActionBundle.objects.filter(proposal__status=Proposal.PROPOSED)
    for action in bundle_actions:
        for policy in CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=action.community_integration):
            _execute_policy(policy, action)
    
    

