from django.apps import apps
from django.conf import settings
import logging
from urllib.parse import quote
import random
import os
import json

logger = logging.getLogger(__name__)


class ActionKind:
    PLATFORM = "platform"
    CONSTITUTION = "constitution"


def default_election_vote_message(policy):
    return (
        "This action is governed by the following policy: " + policy.description + ". Decide between options below:\n"
    )


def default_boolean_vote_message(policy):
    return (
        "This action is governed by the following policy: "
        + policy.description
        + ". Vote with :thumbsup: or :thumbsdown: on this post."
    )

def find_action_cls(app_name: str, codename: str):
    """
    Get the PlatformAction subclass that has the specified codename
    """
    from policyengine.models import PlatformAction

    for cls in apps.get_app_config(app_name).get_models():
        if issubclass(cls, PlatformAction) and cls._meta.model_name == codename:
            return cls
    return None


def get_action_classes(app_name: str):
    """
    Get a list of PlatformAction subclasses defined in the given app
    """
    from policyengine.models import PlatformAction

    actions = []
    for cls in apps.get_app_config(app_name).get_models():
        if issubclass(cls, PlatformAction):
            actions.append(cls)
    return actions


def get_action_content_types(app_name: str):
    from django.contrib.contenttypes.models import ContentType

    return [ContentType.objects.get_for_model(cls) for cls in get_action_classes(app_name)]


def construct_authorize_install_url(request, integration, community=None):
    logger.debug(f"Constructing URL to install '{integration}' to community '{community}'.")

    # Initiate authorization flow to install Metagov to platform.
    # On successful completion, the Metagov Slack plugin will be enabled for the community.

    # Redirect to the plugin-specific install endpoint, which will complete the setup process (ie create the SlackCommunity)
    redirect_uri = f"{settings.SERVER_URL}/{integration}/install"
    encoded_redirect_uri = quote(redirect_uri, safe="")

    # store state in user's session so we can validate it later
    state = "".join([str(random.randint(0, 9)) for i in range(8)])
    request.session["community_install_state"] = state

    # if not specified, metagov will create a new community and pass back the slug
    community_slug = community.metagov_slug if community else ""
    url = f"{settings.METAGOV_URL}/auth/{integration}/authorize?type=app&community={community_slug}&redirect_uri={encoded_redirect_uri}&state={state}"
    logger.debug(url)
    return url


def get_starterkits_info():
    """
    Get a list of all starter-kit names and descriptions.
    """
    starterkits = []
    cur_path = os.path.abspath(os.path.dirname(__file__))
    dir_path = os.path.join(cur_path, f"../starterkits")
    for kit_file in os.listdir(dir_path):
        kit_path = os.path.join(dir_path, kit_file)
        f = open(kit_path)
        data = json.loads(f.read())
        starterkits.append({"name": data["name"], "description": data["description"]})
    return starterkits


def initialize_starterkit_inner(community, kit_data, creator_token=None):
    from policyengine.models import Policy, CommunityRole, CommunityUser
    from django.contrib.auth.models import Permission

    # Initialize platform policies from starter kit
    for policy in kit_data["platform_policies"]:
        Policy.objects.create(**policy, kind=Policy.PLATFORM, community=community)

    # Initialize constitution policies from starter kit
    for policy in kit_data["constitution_policies"]:
        Policy.objects.create(
            **policy,
            kind=Policy.CONSTITUTION,
            community=community,
        )

    # Initialize roles from starter kit
    for role in kit_data["roles"]:
        r = CommunityRole.objects.create(
            role_name=role["name"],
            name=f"{community.platform}: {community.community_name}: {role['name']}",
            description=role["description"],
            community=community,
        )

        if role["is_base_role"]:
            old_base_role = community.base_role
            community.base_role = r
            community.save()
            old_base_role.delete()

        # Add PolicyKit-related permissions
        r.permissions.set(Permission.objects.filter(name__in=role["permissions"]))

        # Add permissions for each PlatformAction
        action_content_types = get_action_content_types(community.platform)
        if "view" in role["permission_sets"]:
            view_perms = Permission.objects.filter(content_type__in=action_content_types, name__startswith="Can view")
            r.permissions.add(*view_perms)
        if "propose" in role["permission_sets"]:
            propose_perms = Permission.objects.filter(
                content_type__in=action_content_types, name__startswith="Can add"
            )
            r.permissions.add(*propose_perms)
        if "execute" in role["permission_sets"]:
            execute_perms = Permission.objects.filter(
                content_type__in=action_content_types, name__startswith="Can execute"
            )
            r.permissions.add(*execute_perms)

        group = None
        if role["user_group"] == "all":
            group = CommunityUser.objects.filter(community=community)
        elif role["user_group"] == "admins":
            group = CommunityUser.objects.filter(community=community, is_community_admin=True)
        elif role["user_group"] == "nonadmins":
            group = CommunityUser.objects.filter(community=community, is_community_admin=False)
        elif role["user_group"] == "creator":
            group = CommunityUser.objects.filter(community=community, access_token=creator_token)

        for user in group:
            r.user_set.add(user)

        r.save()