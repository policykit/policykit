user_group = CommunityRole.objects.create(role_name="fake role", name="testing role")
can_add = Permission.objects.get(name="Can add slack pin message")
user_group.permissions.add(can_add)
community = Community.objects.create()
slack_community = SlackCommunity.objects.create(
    community_name="my test community",
    community=community,
    team_id="TMQ3PKX",
    base_role=user_group,
)
user = SlackUser.objects.create(username="test", community=slack_community)


slack_community = SlackCommunity.objects.all()[0]
all_actions_pass_policy = {
    "filter": "return True",
    "initialize": "pass",
    "notify": "pass",
    "check": "return PASSED",
    "success": "pass",
    "fail": "pass",
}
p = PlatformPolicy.objects.create(
    **all_actions_pass_policy,
    community=slack_community,
    description="all actions pass",
    name="all actions pass",
)
p.save()