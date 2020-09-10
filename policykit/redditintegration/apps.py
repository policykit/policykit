from django.apps import AppConfig


class redditIntegrationConfig(AppConfig):
    name = 'redditintegration'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('RedditUser'))
