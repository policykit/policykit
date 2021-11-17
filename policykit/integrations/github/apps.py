from django.apps import AppConfig


class GithubIntegrationConfig(AppConfig):
    name = 'integrations.github'

    def ready(self):
        import integrations.github.handlers
