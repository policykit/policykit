from django.apps import apps
from django.conf import settings
import logging
from urllib.parse import quote
import random

logger = logging.getLogger(__name__)

def find_action_cls(app_name: str, action_codename: str):
    """
    Get the PlatformAction subclass that has the specified codename
    """
    from policyengine.models import PlatformAction
    for cls in apps.get_app_config(app_name).get_models():
        if issubclass(cls, PlatformAction) and hasattr(cls, "action_codename"):
            if action_codename == getattr(cls, "action_codename"):
                return cls
    return None

def get_action_classes(app_name: str):
    """
    Get a list of PlatformAction subclasses defined in the given app
    """
    from policyengine.models import PlatformAction
    actions = []
    for cls in apps.get_app_config(app_name).get_models():
        if issubclass(cls, PlatformAction) and hasattr(cls, "action_codename"):
            actions.append(cls)
    return actions

def construct_authorize_install_url(request, integration, community=None):
    logger.debug(f"Constructing URL to install '{integration}' to community '{community}'.")

    # Initiate authorization flow to install Metagov to platform.
    # On successful completion, the Metagov Slack plugin will be enabled for the community.

    if community is None:
        # we're creating a new community, so redirect to the install endpoint which will complete
        # the setup process (ie create the SlackCommunity) and redirect to /login when complete.
        redirect_uri = f"{settings.SERVER_URL}/{integration}/install"
    else:
        # we're enabling an integration for an existing community, so redirect to the settings page
        redirect_uri = f"{settings.SERVER_URL}/main/settings"
    encoded_redirect_uri = quote(redirect_uri, safe='')

    # store state in user's session so we can validate it later
    state = "".join([str(random.randint(0, 9)) for i in range(8)])
    request.session['community_install_state'] = state

    # if not specified, metagov will create a new community and pass back the slug
    community_slug = community.metagov_slug if community else ''
    url = f"{settings.METAGOV_URL}/auth/{integration}/authorize?type=app&community={community_slug}&redirect_uri={encoded_redirect_uri}&state={state}"
    logger.debug(url)
    return url