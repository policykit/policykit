from django.contrib.auth.models import Permission
from integrations.slack.models import SlackCommunity, SlackUser
from policyengine.models import CommunityRole

ALL_ACTIONS_PASS = {
    "filter": "return True",
    "initialize": "pass",
    "notify": "pass",
    "check": "return PASSED",
    "success": "pass",
    "fail": "pass",
    "name": "all actions pass",
}

ALL_ACTIONS_PROPOSED = {
    **ALL_ACTIONS_PASS,
    "check": "return PROPOSED",
    "name": "all actions proposed",
}

ALL_ACTIONS_FAIL = {
    **ALL_ACTIONS_PASS,
    "check": "return FAILED",
    "name": "all actions fail",
}


def create_no_platform_community():
    from constitution.models import ConstitutionCommunity

    comm = ConstitutionCommunity.objects.create(community_name="my community")
    print("it worked!")


def create_slack_community_and_user(team_id = "ABC", username="user1"):
    # create initial community
    slack_community = SlackCommunity.objects.create(community_name="slack test community", team_id=team_id)

    # create a base role with permission to propose any action
    user_group = CommunityRole.objects.create(
        role_name="fake role", community=slack_community.community, is_base_role=True
    )
    propose_perms = Permission.objects.filter(name__startswith="Can add")
    user_group.permissions.add(*propose_perms)

    # create a user
    user = SlackUser.objects.create(username=username, community=slack_community)

    return slack_community, user


def create_slack_and_discord_community():
    slack_comm, _ = create_slack_community_and_user()
    from integrations.discord.models import DiscordCommunity

    DiscordCommunity.objects.create(
        community_name="discord test community", community=slack_comm.community, team_id="123"
    )

def create_user_in_slack_community(community: SlackCommunity, username: str):
    return SlackUser.objects.create(username=username, community=community)
