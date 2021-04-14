from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policyengine.models import Proposal, LogAPICall, PlatformPolicy, PlatformAction, BooleanVote, NumberVote
from integrations.discourse.models import DiscourseCommunity, DiscourseUser, DiscourseCreateTopic, DiscourseCreatePost
from policyengine.views import filter_policy, check_policy, initialize_policy
from urllib import parse
import urllib.request
import urllib.error
import json
import datetime
import logging
import json

logger = logging.getLogger(__name__)

def is_policykit_action(community, call_type, topic, username):
    if username == 'PolicyKit': ## TODO: Compare IDs in future, not usernames
        return True

    current_time_minus = datetime.datetime.now() - datetime.timedelta(minutes=2)
    logs = LogAPICall.objects.filter(
        proposal_time__gte=current_time_minus,
        call_type=call_type
    )
    if logs.exists():
        for log in logs:
            j_info = json.loads(log.extra_info)
            if topic['id'] == j_info['id']:
                return True
    return False

@shared_task
def discourse_listener_actions():
    for community in DiscourseCommunity.objects.all():
        actions = []

        url = community.team_id
        api_key = community.api_key

        req = urllib.request.Request(url + '/latest.json')
        req.add_header("User-Api-Key", api_key)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        topics = res['topic_list']['topics']
        users = res['users']

        for topic in topics:
            user_id = topic['posters'][0]['user_id']
            usernames = [u['username'] for u in users if u['id'] == user_id]
            if not usernames:
                logger.error(f"no username found for user id {user_id}, skipping topic")
                continue
            username = usernames[0]
            call_type = '/posts.json'
            if not is_policykit_action(community, call_type, topic, username):
                t = DiscourseCreateTopic.objects.filter(id=topic['id'])
                if not t.exists():
                    # Retrieve raw from first post under topic (created when topic created)
                    req = urllib.request.Request(f"{url}/t/{str(topic['id'])}/posts.json?include_raw=True")
                    req.add_header("User-Api-Key", api_key)
                    resp = urllib.request.urlopen(req)
                    res = json.loads(resp.read().decode('utf-8'))
                    raw = res['post_stream']['posts'][0]['raw']

                    logger.info('Discourse: creating new DiscourseCreateTopic for: ' + topic['title'])
                    new_api_action = DiscourseCreateTopic()
                    new_api_action.community = community
                    new_api_action.title = topic['title']
                    new_api_action.category = topic['category_id']
                    new_api_action.raw = raw
                    new_api_action.id = topic['id']

                    u,_ = DiscourseUser.objects.get_or_create(
                        username=username,
                        community=community
                    )
                    new_api_action.initiator = u
                    actions.append(new_api_action)
        for action in actions:
            action.community_origin = True
            action.is_bundled = False
            action.save()
            if action.community_revert:
                action.revert()

        # Manage proposals
        proposed_actions = PlatformAction.objects.filter(
            community=community,
            proposal__status=Proposal.PROPOSED,
            community_post__isnull=False
        )
        for proposed_action in proposed_actions:
            logger.info('in proposed action loop')
            id = proposed_action.community_post

            req = urllib.request.Request(url + '/posts/' + id + '.json')
            req.add_header("User-Api-Key", api_key)
            resp = urllib.request.urlopen(req)
            res = json.loads(resp.read().decode('utf-8'))
            poll = res['polls'][0]

            # Manage Boolean voting
            for option in poll['options']:
                val = (option['html'] == 'Yes')

                for user in poll['preloaded_voters'][option['id']]:
                    u = DiscourseUser.objects.filter(
                        username=user['id'],
                        community=community
                    )
                    if u.exists():
                        u = u[0]

                        bool_vote = BooleanVote.objects.filter(proposal=proposed_action.proposal, user=u)
                        if bool_vote.exists():
                            vote = bool_vote[0]
                            if vote.boolean_value != val:
                                vote.boolean_value = val
                                vote.save()
                        else:
                            b = BooleanVote.objects.create(proposal=proposed_action.proposal, user=u, boolean_value=val)

            # Update proposal
            logger.info('updating proposal')
            for policy in PlatformPolicy.objects.filter(community=community):
                logger.info('about to filter policy')
                if filter_policy(policy, proposed_action):
                    logger.info('just filtered policy')
                    cond_result = check_policy(policy, proposed_action)
                    if cond_result == Proposal.PASSED:
                        logger.info('passed proposal discourse')
                        pass_policy(policy, proposed_action)
                    elif cond_result == Proposal.FAILED:
                        logger.info('failed proposal discourse')
                        fail_policy(policy, proposed_action)
