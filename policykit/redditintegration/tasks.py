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

@shared_task
def reddit_listener_actions():
    
    for community in RedditCommunity.objects.all():
        
        actions = []
        
        res = community.make_call('r/policykit/about/unmoderated')
        
        for item in res['data']['children']:
            data = item['data']
            
            logger.info(data)

            post_exists = RedditMakePost.objects.filter(name=data['name'])
            
            logger.info(post_exists)
            
            if not post_exists.exists():
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
                    initialize_code(policy, action)
                    cond_result = check_policy_code(policy, action)
                    if cond_result == Proposal.PROPOSED or cond_result == Proposal.FAILED:
                        action.revert()
        
    
    logger.info('reddit_task')
    pass
    

