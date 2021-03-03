from django.db import models
from policyengine.models import PlatformAction, PlatformPolicy


class ExternalProcess(models.Model):
    json_data = models.CharField(max_length=500, blank=True, null=True)
    policy = models.ForeignKey(PlatformPolicy, on_delete=models.CASCADE)
    action = models.ForeignKey(PlatformAction, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['policy', 'action']

# TODO add generic integrator models, so that Metagov can act as a connector for various external platforms
# ExternalCommunity
# ExternalUser
# ExternalPlatformAction]

