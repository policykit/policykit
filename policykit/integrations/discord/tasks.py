from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policykit.settings import DISCORD_BOT_TOKEN
from policyengine.models import Proposal, LogAPICall, PlatformPolicy, PlatformAction, BooleanVote, NumberVote
from integrations.discord.models import DiscordCommunity, DiscordUser, DiscordPostMessage
from policyengine.views import filter_policy, check_policy, initialize_policy
from urllib import parse
import urllib.request
import urllib.error
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
            for log in logs:
                j_info = json.loads(log.extra_info)
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
            if channel['type'] != 0: # We only want to check text channels
                continue

            channel_id = channel['id']

            # Post Message
            call_type = ('channels/%s/messages' % channel_id)

            req = urllib.request.Request('https://discordapp.com/api/channels/%s/messages' % channel_id)
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            req.add_header('Authorization', 'Bot %s' % DISCORD_BOT_TOKEN)
            req.add_header("User-Agent", "Mozilla/5.0") # yes, this is strange. discord requires it when using urllib for some weird reason
            resp = urllib.request.urlopen(req)
            messages = json.loads(resp.read().decode('utf-8'))

            for message in messages:
                if not is_policykit_action(community, message['id'], 'id', call_type):
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

            # Rename Channel
            """call_type = ('channels/%s' % channel_id)

            if not is_policykit_action(community, channel['name'], 'name', call_type):
                new_api_action = DiscordRenameChannel()
                new_api_action.community = community
                new_api_action.name = channel['name']
                new_api_action.channel = channel['id']

                actions.append(new_api_action)"""

        for action in actions:
            action.community_origin = True
            action.is_bundled = False
            action.save()
            if action.community_revert:
                action.revert()

        # Boolean voting

        logger.info('Discord: About to filter platform actions (2)')
        proposed_actions = PlatformAction.objects.filter(
            community=community,
            proposal__status=Proposal.PROPOSED,
            community_post__isnull=False
        )

        logger.info("Discord: number of platform actions is:")
        logger.info(proposed_actions.count())

        for proposed_action in proposed_actions:
            logger.info('Discord proposed action:')
            logger.info('Channel: ' + proposed_action.channel)
            logger.info('Community post: ' + proposed_action.community_post)
            channel_id = proposed_action.channel
            message_id = proposed_action.community_post

            # Check if community post still exists
            call = ('channels/%s/messages/%s' % (channel_id, message_id))
            try:
                community.make_call(call)
            except urllib.error.HTTPError as e:
                logger.info('entered outside except')
                logger.info(e.code)
                if e.code == 404: # Message not found
                    logger.info('about to delete')
                    proposed_action.delete()
                    logger.info('deleted')
                continue

            for reaction in [EMOJI_LIKE_ENCODED, EMOJI_DISLIKE_ENCODED]:
                call = ('channels/%s/messages/%s/reactions/%s' % (channel_id, message_id, reaction))
                logger.info("Discord: About to check reactions of message with ID: " + message_id)
                users_with_reaction = community.make_call(call)
                logger.info("Discord: Just retrieved reactions of message with ID: " + message_id)

                for user in users_with_reaction:
                    u = DiscordUser.objects.filter(username=user.id, community=community)
                    if u.exists():
                        u = u[0]

                        # Check for Boolean votes
                        if reaction in [EMOJI_LIKE_ENCODED, EMOJI_DISLIKE_ENCODED]:
                            if reaction == EMOJI_LIKE_ENCODED:
                                logger.info("Discord: like emoji found for message with ID: " + message_id)
                            if reaction == EMOJI_DISLIKE_ENCODED:
                                logger.info("Discord: dislike emoji found for message with ID: " + message_id)
                            val = (reaction == EMOJI_LIKE_ENCODED)

                            bool_vote = BooleanVote.objects.filter(proposal=proposed_action.proposal, user=u)

                            if bool_vote.exists():
                                vote = bool_vote[0]
                                if vote.boolean_value != val:
                                    vote.boolean_value = val
                                    vote.save()
                            else:
                                logger.info("Discord: About to create vote object for message with ID: " + message_id)
                                b = BooleanVote.objects.create(proposal=proposed_action.proposal, user=u, boolean_value=val)
                                logger.info("Discord: Just created vote object for message with ID: " + message_id)
