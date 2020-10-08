from django.apps import AppConfig


class slackIntegrationConfig(AppConfig):
    name = 'slackintegration'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('SlackUser'))
