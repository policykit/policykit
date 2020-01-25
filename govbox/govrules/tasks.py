# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from govrules.models import UserVote


@shared_task
def count_votes():
    return UserVote.objects.count()