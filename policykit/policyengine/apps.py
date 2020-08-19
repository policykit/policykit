from django.apps import AppConfig


class policyEngineConfig(AppConfig):
    name = 'policyengine'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('PlatformAction'))
