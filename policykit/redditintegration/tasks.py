# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policyengine.models import Proposal, CommunityPolicy
from redditintegration.models import RedditCommunity, RedditUser, RedditMakePost
from policyengine.views import check_filter_code, check_policy_code, initialize_code
import datetime
import logging

logger = logging.getLogger(__name__)

def is_policykit_action(name):
    community_post = RedditMakePost.objects.filter(community_post=name)
    if community_post.exists():
        return True
    return False

@shared_task
def reddit_listener_actions():
    
    for community in RedditCommunity.objects.all():
        
        actions = []
        
        res = community.make_call('r/policykit/about/unmoderated')
        
        for item in res['data']['children']:
            data = item['data']
            
            if not is_policykit_action(data['name']):
    
                post_exists = RedditMakePost.objects.filter(name=data['name'])
                
                if not post_exists.exists():
                    logger.info('make new action')
                    
                    new_api_action = RedditMakePost()
                    new_api_action.community = community
                    new_api_action.text = data['selftext']
                    new_api_action.title = data['title']
                    new_api_action.name = data['name']
        
                    u,_ = RedditUser.objects.get_or_create(username=data['author'],
                                                           community=community)
                    new_api_action.initiator = u
                    actions.append(new_api_action)
                    
        
        for action in actions:
            for policy in CommunityPolicy.objects.filter(community=action.community):
                if check_filter_code(policy, action):
                    if not action.pk:
                        action.community_origin = True
                        action.is_bundled = False
                        action.save()
                        logger.info('action saved')
                    cond_result = check_policy_code(policy, action)
                    logger.info(cond_result)
                    if cond_result == Proposal.PROPOSED or cond_result == Proposal.FAILED:
                        logger.info('revert')
                        action.revert()
        
    
    logger.info('reddit_task')
    pass
    

