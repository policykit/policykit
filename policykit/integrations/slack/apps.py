from django.apps import AppConfig


class slackIntegrationConfig(AppConfig):
    name = 'integrations.slack'

    def ready(self):
        import integrations.slack.handlers

        from actstream import registry
        registry.register(self.get_model('SlackUser'))
