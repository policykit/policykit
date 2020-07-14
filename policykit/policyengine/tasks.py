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
        
    #need to check if user has propose (add) permission before proposing
    #need to check if user has view permission for admin site?
    #need to check if user has execute permission here
    community_actions = CommunityAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    app_name = ''
    for action in community_actions:
        
        logger.info(action)
        
        #if they have execute permission, then skip all this, and just let them 'exec' the code, with the action_code
        if isinstance(action.community, SlackCommunity):
            app_name = 'slackintegration'
        elif isinstance(action.community, RedditCommunity):
            app_name = 'redditintegration'

        '''if action.initiator.has_perm(app_name + '.can_execute_' + action.action_codename):
            action.execute()
        else:'''
        if True:
            for policy in CommunityPolicy.objects.filter(community=action.community):
                _execute_policy(policy, action)

    bundle_actions = CommunityActionBundle.objects.filter(proposal__status=Proposal.PROPOSED)
    for action in bundle_actions:
        #if they have execute permission, then skip all this, and just let them 'exec' the code, with the action_code
        if isinstance(action.community, SlackCommunity):
            app_name = 'slackintegration'
        elif isinstance(action.community, RedditCommunity):
            app_name = 'redditintegration'
        
        '''if action.initiator.has_perm(app_name + '.can_execute_' + action.action_codename):
            action.execute()
        else:'''
        if True:
            for policy in CommunityPolicy.objects.filter(community=action.community):
                _execute_policy(policy, action)
    
    constitution_actions = ConstitutionAction.objects.filter(proposal__status=Proposal.PROPOSED, is_bundled=False)
    for action in constitution_actions:
        #if they have execute permission, then skip all this, and just let them 'exec' the code, with the action_code
        '''if action.initiator.has_perm('policyengine.can_execute_' + action.action_codename):
            action.execute()
        else:'''
        if True:
            for policy in ConstitutionPolicy.objects.filter(community=action.community):
                _execute_policy(policy, action)
    

