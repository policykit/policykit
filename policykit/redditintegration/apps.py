from django.apps import AppConfig


class RedditintegrationConfig(AppConfig):
    name = 'redditintegration'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('RedditUser'))
