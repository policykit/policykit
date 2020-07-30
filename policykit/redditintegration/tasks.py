# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policyengine.models import Proposal, LogAPICall, PlatformPolicy, PlatfoormAction, BooleanVote, NumberVote
from redditintegration.models import RedditCommunity, RedditUser, RedditMakePost
from policyengine.views import filter_policy, check_policy, initialize_policy
import datetime
import logging
import json

logger = logging.getLogger(__name__)

def is_policykit_action(community, name, call_type, test_a, test_b):
    community_post = RedditMakePost.objects.filter(community_post=name)
    if community_post.exists():
        logger.info('approve PolicyKit post')
        community.make_call('api/approve', {'id': name})
        return True
    else:
        current_time_minus = datetime.datetime.now() - datetime.timedelta(minutes=2)
        logs = LogAPICall.objects.filter(proposal_time__gte=current_time_minus,
                                                call_type=call_type)
        if logs.exists():
            logger.info("checking API logging")
            for log in logs:
                j_info = json.loads(log.extra_info)
                if test_a == j_info[test_b]:
                    logger.info("checking API logging FOUND")
                    return True
    return False

@shared_task
def reddit_listener_actions():

    for community in RedditCommunity.objects.all():
        actions = []

        res = community.make_call('r/policykit/about/unmoderated')

        call_type = 'api/submit'

        for item in res['data']['children']:
            data = item['data']

            if not is_policykit_action(community, data['name'], call_type, data['title'], 'title'):

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
            for policy in PlatformPolicy.objects.filter(community=action.community):
                if filter_policy(policy, action):
                    if not action.pk:
                        action.community_origin = True
                        action.is_bundled = False
                        action.save()
                        logger.info('action saved')
                    cond_result = check_policy(policy, action)
                    logger.info(cond_result)
                    if cond_result == Proposal.PROPOSED or cond_result == Proposal.FAILED:
                        logger.info('revert')
                        action.revert()



        # look for votes

        proposed_actions = PlatformAction.objects.filter(community=community,
                                                          proposal__status=Proposal.PROPOSED,
                                                          community_post__isnull=False
                                                          )

        for proposed_action in proposed_actions:

            id = proposed_action.community_post.split('_')[1]

            call = 'r/policykit/comments/' + id + '.json'
            res = community.make_call(call)
            replies = res[1]['data']['children']

            for reply in replies:
                data = reply['data']

                text = data['body']

                logger.info(text)

                val = None
                if '\\-1' in text:
                    val = False
                elif '\\+1' in text:
                    val = True

                if val != None:
                    username = data['author']
                    u = RedditUser.objects.filter(username=username,
                                                  community=community)

                    if u.exists():
                        u = u[0]
                        bool_vote = BooleanVote.objects.filter(proposal=proposed_action.proposal,
                                                               user=u)
                        if bool_vote.exists():
                            vote = bool_vote[0]
                            if vote.boolean_value != val:
                                vote.boolean_value = val
                                vote.save()
                        else:
                            b = BooleanVote.objects.create(proposal=proposed_action.proposal,
                                                           user=u,
                                                           boolean_value=val)
                            logger.info('created vote')
