def get_slack_user_fields(user_info):
    """
    Get SlackUser fields from Slack 'user' type

    https://api.slack.com/types/user
    """
    return {
        "username": user_info["id"],
        "readable_name": user_info["profile"]["real_name"],
        "is_community_admin": user_info["is_admin"] and not user_info["is_bot"],
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
