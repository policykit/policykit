from django.apps import AppConfig


class discordIntegrationConfig(AppConfig):
    name = 'integrations.discord'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('DiscordUser'))
