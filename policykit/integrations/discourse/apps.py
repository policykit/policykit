from django.apps import AppConfig


class discourseIntegrationConfig(AppConfig):
    name = 'integrations.discourse'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('DiscourseUser'))
