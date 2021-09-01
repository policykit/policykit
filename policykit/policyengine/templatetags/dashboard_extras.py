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
    if num == 1:
        return display_names[0]
    if num == 2:
        return f"{display_names[0]} and {display_names[1]}"
    if num == 3:
        return f"{display_names[0]}, {display_names[1]}, and {display_names[2]}"
    if num > 3:
        return f"{display_names[0]}, {display_names[1]}, and {num-2} more"