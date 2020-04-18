# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
import logging

logger = logging.getLogger(__name__)

@shared_task
def reddit_listener_actions():
    logger.info('reddit_task')
    pass
    

