import logging

from django.dispatch import receiver
from metagov.core.signals import platform_event_created
from metagov.core.models import Plugin
from policyengine.models import WebhookTriggerAction, Community

logger = logging.getLogger(__name__)


@receiver(platform_event_created)
def metagov_event_receiver(sender, instance, event_type, data, initiator, **kwargs):
    # Need to check if this is a Plugin using subclass
    # instead of using `sender` because these are Proxy models.
    if not issubclass(sender, Plugin):
        return

    if initiator.get("is_metagov_bot"):
        return

    prefixed_event_type = f"{instance.name}.{event_type}"
    try:
        community = Community.objects.get(metagov_slug=instance.community.slug)
    except Community.DoesNotExist:
        logger.warn(f"No Community matches {instance}, ignoring {prefixed_event_type}")
        return
    logger.debug(f"Received {prefixed_event_type} for community {community}")

    # If we have a CommunityPlatform for this platform, link the trigger to it
    community_platform = community.get_platform_community(instance.name)
    if not community_platform:
        # If not, use constitution community as linked CommunityPlatform (even though its not a constitutional event...)
        community_platform = community.constitution_community

    trigger = WebhookTriggerAction(event_type=prefixed_event_type, data=data, community=community_platform)
    trigger.evaluate()
