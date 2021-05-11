import logging
from django.db import models
from six import python_2_unicode_compatible
from django.utils.translation import gettext_lazy as _
from policyengine.models import Community

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
    community = models.ForeignKey(Community, blank=True, on_delete=models.CASCADE)
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
