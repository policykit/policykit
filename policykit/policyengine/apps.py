from django.apps import AppConfig

#registry of model streams
class policyEngineConfig(AppConfig):
    name = 'policyengine'

    def ready(self):
        import policyengine.handlers
        from actstream import registry
        registry.register(self.get_model('GovernableAction'))
        registry.register(self.get_model('GovernableActionBundle'))
        registry.register(self.get_model('Policy'))
        registry.register(self.get_model('CommunityUser'))
        registry.register(self.get_model('CommunityRole'))
        registry.register(self.get_model('BooleanVote'))
        registry.register(self.get_model('NumberVote'))
        registry.register(self.get_model('Proposal'))
        registry.register(self.get_model('CommunityDoc'))
