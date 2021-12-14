from django.apps import AppConfig

class discordIntegrationConfig(AppConfig):
    name = 'integrations.discord'

    def ready(self):
        import integrations.discord.handlers

        from actstream import registry
        registry.register(self.get_model('DiscordUser'))
