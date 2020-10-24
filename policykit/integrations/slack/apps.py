from django.apps import AppConfig


class slackIntegrationConfig(AppConfig):
    name = 'integrations.slack'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('SlackUser'))
