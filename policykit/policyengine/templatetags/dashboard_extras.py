from django import template

register = template.Library()


@register.filter(name="cut")
def cut(value, arg):
    """Removes all values of arg from the given string"""
    return value.replace(arg, "")


@register.filter(name="user_roles")
def user_roles(value):
    """List all roles for a given user"""
    return list(value.groups.all().values_list("communityrole__role_name", flat=True))


@register.filter(name="role_users_string")
def role_users_string(value):
    """List users in role"""
    num = value.user_set.count()
    users = value.user_set.all()[0:3]
    display_names = [u.communityuser.readable_name or u.username for u in users]
    return comma_separated(display_names, num)


@register.filter(name="action_types")
def action_types(value):
    """List action types on policy"""
    if not value.action_types.exists():
        return None
    num = value.action_types.count()
    display_names = value.action_types.all()[0:3].values_list("codename", flat=True)
    return comma_separated(display_names, num)


def comma_separated(display_names, num):
    if num == 1:
        return display_names[0]
    if num == 2:
        return f"{display_names[0]} and {display_names[1]}"
    if num == 3:
        return f"{display_names[0]}, {display_names[1]}, and {display_names[2]}"
    if num > 3:
        return f"{display_names[0]}, {display_names[1]}, and {num-2} more"