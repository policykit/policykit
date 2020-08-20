from django.apps import AppConfig


class policyEngineConfig(AppConfig):
    name = 'policyengine'

    def ready(self):
        from actstream import registry
        registry.register(self.get_model('PlatformPolicy'))
        registry.register(self.get_model('PlatformAction'))
        registry.register(self.get_model('PlatformActionBundle'))
        registry.register(self.get_model('ConstitutionPolicy'))
        registry.register(self.get_model('ConstitutionAction'))
        registry.register(self.get_model('ConstitutionActionBundle'))
        registry.register(self.get_model('CommunityUser'))
        registry.register(self.get_model('CommunityRole'))
        registry.register(self.get_model('UserVote'))
        registry.register(self.get_model('BooleanVote'))
        registry.register(self.get_model('NumberVote'))
        registry.register(self.get_model('Proposal'))

