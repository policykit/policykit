from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policykit.settings import DISCORD_BOT_TOKEN
from policyengine.models import Proposal, LogAPICall, PlatformPolicy, PlatformAction, BooleanVote, NumberVote
from discordintegration.models import DiscordCommunity, DiscordUser, DiscordPostMessage
from policyengine.views import filter_policy, check_policy, initialize_policy
from urllib import parse
import urllib.request
import json
import datetime
import logging
import json

logger = logging.getLogger(__name__)

# Used for Boolean and Number voting
EMOJI_LIKE_ENCODED = '%f0%9f%91%8d'
EMOJI_DISLIKE_ENCODED = '%f0%9f%91%8e'
EMOJI_ZERO_ENCODED = '0%ef%b8%8f%e2%83%a3'
EMOJI_ONE_ENCODED = '1%ef%b8%8f%e2%83%a3'
EMOJI_TWO_ENCODED = '2%ef%b8%8f%e2%83%a3'
EMOJI_THREE_ENCODED = '3%ef%b8%8f%e2%83%a3'
EMOJI_FOUR_ENCODED = '4%ef%b8%8f%e2%83%a3'
EMOJI_FIVE_ENCODED = '5%ef%b8%8f%e2%83%a3'
EMOJI_SIX_ENCODED = '6%ef%b8%8f%e2%83%a3'
EMOJI_SEVEN_ENCODED = '7%ef%b8%8f%e2%83%a3'
EMOJI_EIGHT_ENCODED = '8%ef%b8%8f%e2%83%a3'
EMOJI_NINE_ENCODED = '9%ef%b8%8f%e2%83%a3'

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
                        new_api_action = DiscordPostMessage()
                        new_api_action.community = community
                        new_api_action.text = message['content']
                        new_api_action.channel = message['channel_id']
                        new_api_action.id = message['id']

                        u,_ = DiscordUser.objects.get_or_create(username=message['author']['id'],
                                                               community=community)
                        new_api_action.initiator = u
                        actions.append(new_api_action)
                        logger.info('added action')

        logger.info("ACTION TIME!!!")
        for action in actions:
            logger.info("Action:")
            logger.info(action)
            for policy in PlatformPolicy.objects.filter(community=action.community):
                logger.info("Policy:")
                logger.info(policy)
                if filter_policy(policy, action):
                    logger.info("passed filter")
                    if not action.pk:
                        action.community_origin = True
                        action.is_bundled = False
                        logger.info('about to save')
                        action.save()
                        logger.info('action saved')
                    logger.info('not pk')
                    check_result = check_policy(policy, action)
                    logger.info('Check results:')
                    logger.info(check_result)
                    if check_result == Proposal.PROPOSED or check_result == Proposal.FAILED:
                        logger.info('revert')
                        action.revert()

        # Boolean voting

        proposed_actions = PlatformAction.objects.filter(
            community=community,
            proposal_status=Proposal.PROPOSED,
            community_post__isnull=False
        )

        for proposed_action in proposed_actions:
            channel_id = proposed_action.channel
            message_id = proposed_action.id

            for reaction in [EMOJI_LIKE_ENCODED, EMOJI_DISLIKE_ENCODED, EMOJI_ZERO_ENCODED, EMOJI_ONE_ENCODED, EMOJI_TWO_ENCODED, EMOJI_THREE_ENCODED, EMOJI_FOUR_ENCODED, EMOJI_FIVE_ENCODED, EMOJI_SIX_ENCODED, EMOJI_SEVEN_ENCODED, EMOJI_EIGHT_ENCODED, EMOJI_NINE_ENCODED]:
                call = ('channels/%s/messages/%s/reactions/%s' % (channel_id, message_id, reaction))
                users_with_reaction = community.make_call(call)

                for user in users_with_reaction:
                    u = DiscordUser.objects.filter(username=user.id, community=community)

                    if u.exists():
                        u = u[0]

                        # Check for Boolean votes
                        if reaction in [EMOJI_LIKE_ENCODED, EMOJI_DISLIKE_ENCODED]:
                            bool_vote = BooleanVote.objects.filter(proposal=proposed_action.proposal, user=u)

                            if reaction == EMOJI_LIKE_ENCODED:
                                val = True
                            else:
                                val = False

                            if bool_vote.exists():
                                vote = bool_vote[0]
                                if vote.boolean_value != val:
                                    vote.boolean_value = val
                                    vote.save()
                            else:
                                b = BooleanVote.objects.create(proposal=proposed_action.proposal, user=u, boolean_value=val)
