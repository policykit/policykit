import logging
from django.db import models
from six import python_2_unicode_compatible
from django.utils.translation import gettext_lazy as _
from policyengine.models import Community, Proposal

LOG_LEVELS = (
    (logging.NOTSET, _("NotSet")),
    (logging.INFO, _("Info")),
    (logging.WARNING, _("Warning")),
    (logging.DEBUG, _("Debug")),
    (logging.ERROR, _("Error")),
    (logging.FATAL, _("Fatal")),
)


@python_2_unicode_compatible
class EvaluationLog(models.Model):
    community = models.ForeignKey(Community, blank=True, null=True, on_delete=models.SET_NULL)
    proposal = models.ForeignKey(Proposal, blank=True, null=True, on_delete=models.SET_NULL)
    policy_str = models.CharField(max_length=150, blank=True)
    action_str = models.CharField(max_length=150, blank=True)

    logger_name = models.CharField(max_length=100)
    level = models.PositiveSmallIntegerField(choices=LOG_LEVELS, default=logging.ERROR, db_index=True)
    msg = models.TextField(verbose_name="Message")
    trace = models.TextField(blank=True, null=True)
    create_datetime = models.DateTimeField(auto_now_add=True, verbose_name="Created at")

    def __str__(self):
        return self.msg

    class Meta:
        ordering = ("-create_datetime",)
        verbose_name_plural = verbose_name = "Logging"

    def action(self):
        if self.proposal and self.proposal.action:
            return self.proposal.action
        return self.action_str

    def policy(self):
        if self.proposal and self.proposal.policy:
            return self.proposal.policy
        return self.policy_str