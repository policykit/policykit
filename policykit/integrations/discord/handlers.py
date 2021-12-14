import logging

from django.dispatch import receiver
from integrations.discord.models import (
    DiscordCommunity,
    DiscordSlashCommand,
    DISCORD_SLASH_COMMAND_NAME,
    DISCORD_SLASH_COMMAND_OPTION,
)
from metagov.core.signals import governance_process_updated, platform_event_created
from metagov.plugins.discord.models import Discord, DiscordVote
from policyengine.models import (
    BooleanVote,
    NumberVote,
    Proposal,
    ChoiceVote,
)

logger = logging.getLogger(__name__)


"""
Django signal handlers
"""


@receiver(platform_event_created, sender=Discord)
def discord_event_receiver(sender, instance, event_type, data, initiator, **kwargs):
    """
    Example "data" payload for slash command "/policykit command: 'hello world'"

        {'application_id': '0000000',
        'channel_id': '0000000',
        'data': {
            'id': '0000000',
            'name': 'policykit',
            'options': [
                {'name': 'command', 'type': 3, 'value': 'hello world'}
            ],
            'type': 1
        },
        'guild_id': '0000000',
        'id': '0000000',
        'member': {
            'avatar': None,
            'communication_disabled_until': None,
            'deaf': False,
            'is_pending': False,
            'joined_at': '2020-11-25T18:41:50.890000+00:00',
            'mute': False,
            'nick': None,
            'pending': False,
            'permissions': '0000000',
            'premium_since': None,
            'roles': [],
            'user': {'avatar': None,
            'discriminator': '0000000',
            'id': '0000000',
            'public_flags': 0,
            'username': 'miri'}
        },
        'token': 'REDACTED',
        'type': 2,
        'version': 1}
    """
    logger.debug(f"Received {event_type} event from {instance}")
    logger.debug(data)

    try:
        discord_community = DiscordCommunity.objects.get(
            team_id=instance.community_platform_id, community__metagov_slug=instance.community.slug
        )
    except DiscordCommunity.DoesNotExist:
        logger.warn(f"No DiscordCommunity matches {instance}")
        return

    if event_type != "slash_command":
        logger.debug(f"Ignoring event '{event_type}', not recognized")
        return

    if data["data"]["name"] != DISCORD_SLASH_COMMAND_NAME:
        logger.debug(f"Ignoring slash command, not recognized")
        return

    command_values = [x["value"] for x in data["data"]["options"] if x["name"] == DISCORD_SLASH_COMMAND_OPTION]
    if not command_values:
        logger.debug(f"Ignoring slash command, option value not found")
        return
    command_value = command_values[0]

    user_data = data["member"]["user"] if data["member"] else data["user"]
    logger.debug(f"sent by user: {user_data}")

    user, _ = discord_community._update_or_create_user(user_data)
    action = DiscordSlashCommand.objects.create(
        community=discord_community,
        channel=data["channel_id"],
        value=command_value,
        interaction_token=data["token"],
        initiator=user,
    )

    action.evaluate()


@receiver(governance_process_updated, sender=DiscordVote)
def discord_vote_updated_receiver(sender, instance, status, outcome, errors, **kwargs):
    logger.debug(f">>> got discord vote event {outcome}")