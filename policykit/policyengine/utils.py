from django.apps import apps

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

def get_action_codenames(app_name: str):
    """
    Get a list of action_codenames for PlatformAction models defined in the given app
    """
    from policyengine.models import PlatformAction
    action_list = []
    for cls in apps.get_app_config(app_name).get_models():
            if issubclass(cls, PlatformAction) and hasattr(cls, "action_codename"):
                codename = getattr(cls, "action_codename")
                action_list.append(codename)
    return action_list