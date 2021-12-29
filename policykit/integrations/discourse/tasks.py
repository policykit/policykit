from __future__ import absolute_import, unicode_literals

from celery import shared_task
from django.conf import settings
from policyengine.models import Proposal, GovernableAction, BooleanVote
from integrations.discourse.models import DiscourseCommunity, DiscourseUser, DiscourseCreateTopic
import urllib.request
import urllib.error
import json
import datetime
import logging
import json

logger = logging.getLogger(__name__)

def should_create_action(community, call_type, topic, username):
    # If topic already has an object, don't create a new object for it.
    if DiscourseCreateTopic.objects.filter(topic_id=topic['id']).exists():
        return False

    created_at = topic['created_at']
    created_at = created_at.replace("Z", "+00:00")
    created_at = datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S.%f+00:00")

    now = datetime.datetime.now()

    # If topic is more than twice the Celery beat frequency seconds old,
    # don't create an object for it. This way, we only create objects for
    # topics created after PolicyKit has been installed to the community.
    recent_time = 2 * settings.CELERY_BEAT_FREQUENCY
    if now - created_at > datetime.timedelta(seconds=recent_time):
        return False

    return True

@shared_task
def discourse_listener_actions():
    for community in DiscourseCommunity.objects.all():
        actions = []

        url = community.team_id
        api_key = community.api_key

        req = urllib.request.Request(url + '/latest.json')
        req.add_header("User-Api-Key", api_key)
        resp = urllib.request.urlopen(req)
        logger.info(f"topics response: {resp.status} {resp.reason}")
        res = json.loads(resp.read().decode('utf-8'))
        topics = res['topic_list']['topics']
        users = res['users']
        logger.info(f"{len(topics)} topics")
        for topic in topics:
            user_id = topic['posters'][0]['user_id']
            usernames = [u['username'] for u in users if u['id'] == user_id]
            if not usernames:
                logger.error(f"no username found for user id {user_id}, skipping topic")
                continue
            username = usernames[0]
            call_type = '/posts.json'
            if should_create_action(community, call_type, topic, username):
                logger.info(f"creating new DiscourseCreateTopic object for topic {topic['title']}")

                # Retrieve raw from first post under topic (created when topic created)
                req = urllib.request.Request(f"{url}/t/{str(topic['id'])}/posts.json?include_raw=True")
                req.add_header("User-Api-Key", api_key)
                resp = urllib.request.urlopen(req)
                logger.info(f"raw post response: {resp.status} {resp.reason}")
                res = json.loads(resp.read().decode('utf-8'))
                raw = res['post_stream']['posts'][0]['raw']

                new_api_action = DiscourseCreateTopic()
                new_api_action.community = community
                new_api_action.title = topic['title']
                new_api_action.category = topic['category_id']
                new_api_action.raw = raw
                new_api_action.topic_id = topic['id']

                u,_ = DiscourseUser.objects.get_or_create(
                    username=username,
                    community=community
                )
                new_api_action.initiator = u
                actions.append(new_api_action)
        logger.info(f"{len(actions)} actions created")
        for action in actions:
            action.community_origin = True
            action.save()
            if action.community_revert:
                action._revert()

        # Manage proposals
        pending_proposals = Proposal.objects.filter(
            status=Proposal.PROPOSED,
            action__community=community,
            action__vote_post_id__isnull=False
        )
        for proposal in pending_proposals:
            id = proposal.vote_post_id

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

                        bool_vote = BooleanVote.objects.filter(proposal=proposal, user=u)
                        if bool_vote.exists():
                            vote = bool_vote[0]
                            if vote.boolean_value != val:
                                vote.boolean_value = val
                                vote.save()
                        else:
                            b = BooleanVote.objects.create(proposal=proposal, user=u, boolean_value=val)
