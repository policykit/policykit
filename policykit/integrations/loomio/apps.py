from django.apps import AppConfig


class LoomioIntegrationConfig(AppConfig):
    name = 'integrations.loomio'

    def ready(self):
        import integrations.loomio.handlers
