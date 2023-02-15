def get_discourse_user_fields(user_info, community):
    is_bot = user_info['id'] < 0
    avatar_small = user_info['avatar_template'].replace("{size}", "45")
    return {
        'username': user_info['username'],
        'readable_name': user_info['name'] or user_info['username'],
        'is_community_admin': user_info['admin'] and not is_bot,
        'avatar': community.team_id + avatar_small
    }