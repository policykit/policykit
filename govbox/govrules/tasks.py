# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from govrules.models import UserVote
from govbox.celery import app


@shared_task
def count_votes():
    return UserVote.objects.count()
