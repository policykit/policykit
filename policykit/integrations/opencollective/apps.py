from django.apps import AppConfig


class OpencollectiveIntegrationConfig(AppConfig):
    name = 'integrations.opencollective'

    def ready(self):
        import integrations.opencollective.handlers
