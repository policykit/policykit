from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policykit.settings import DISCORD_BOT_TOKEN
from policyengine.models import Proposal, LogAPICall, CommunityPolicy, CommunityAction, BooleanVote, NumberVote
from discordintegration.models import DiscordCommunity, DiscordUser, DiscordPostMessage
from policyengine.views import filter_policy, check_policy, initialize_policy
from urllib import parse
import urllib.request
import json
import datetime
import logging
import json

logger = logging.getLogger(__name__)

def is_policykit_action(integration, test_a, test_b, api_name):
    community_post = DiscordPostMessage.objects.filter(community_post=test_a)
    if community_post.exists():
        return True
    else:
        current_time_minus = datetime.datetime.now() - datetime.timedelta(minutes=2)
        logs = LogAPICall.objects.filter(proposal_time__gte=current_time_minus,
                                                call_type=integration.API + api_name)
        if logs.exists():
            logger.info("checking API logging (discord)")
            for log in logs:
                j_info = json.loads(log.extra_info)
                logger.info("extra info:")
                logger.info(j_info)
                if test_a == j_info[test_b]:
                    return True
    return False

@shared_task
def discord_listener_actions():
    for community in DiscordCommunity.objects.all():
        actions = []

        req = urllib.request.Request('https://discordapp.com/api/guilds/%s/channels' % community.team_id)
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
        req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
        resp = urllib.request.urlopen(req)
        channels = json.loads(resp.read().decode('utf-8'))

        for channel in channels:
            channel_id = channel['id']

            call_type = ('channels/%s/messages' % channel_id)

            req = urllib.request.Request('https://discordapp.com/api/channels/%s/messages' % channel_id)
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
            req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
            resp = urllib.request.urlopen(req)
            messages = json.loads(resp.read().decode('utf-8'))

            for message in messages:
                logger.info('Message:')
                logger.info(message['content'])
                if not is_policykit_action(community, message['id'], 'id', call_type):
                    logger.info('not already policykit action')
                    post_exists = DiscordPostMessage.objects.filter(id=message['id'])

                    if not post_exists.exists():
                        logger.info('make new action')

                        new_api_action = DiscordPostMessage()
                        new_api_action.community = community
                        new_api_action.text = message['content']
                        new_api_action.channel = message['channel_id']

                        u,_ = DiscordUser.objects.get_or_create(username=message['author']['id'],
                                                               community=community)
                        new_api_action.initiator = u
                        actions.append(new_api_action)

                        logger.info('successfully created new action')

        for action in actions:
            for policy in CommunityPolicy.objects.filter(community=action.community):
                if filter_policy(policy, action):
                    if not action.pk:
                        action.community_origin = True
                        action.is_bundled = False
                        action.save()
                        logger.info('action saved')
                    check_result = check_policy(policy, action)
                    logger.info(check_result)
                    if check_result == Proposal.PROPOSED or check_result == Proposal.FAILED:
                        logger.info('revert')
                        action.revert()
