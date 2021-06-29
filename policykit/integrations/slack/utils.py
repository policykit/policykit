def get_slack_user_fields(user_info):
    """
    Get SlackUser fields from Slack 'user' type

    https://api.slack.com/types/user
    """
    return {
        "username": user_info["id"],
        "readable_name": user_info["profile"]["real_name"],
        "avatar": user_info["profile"]["image_24"],
    }


def get_admin_user_token(platform_community):
    from integrations.slack.models import SlackUser

    admin_user = SlackUser.objects.filter(
        community=platform_community, is_community_admin=True, access_token__isnull=False
    ).first()
    if admin_user:
        return admin_user.access_token
    return None


def reaction_to_boolean(reaction: str):
    if reaction == "+1" or reaction.startswith("+1::skin-tone-"):
        return True
    if reaction == "-1" or reaction.startswith("-1::skin-tone-"):
        return False
    return None
