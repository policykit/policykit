# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from govrules.models import UserVote, ActionMeasure, Measure, RuleMeasure
from govbox.celery import app
from govrules.views import *

@shared_task
def consider_proposed_actions():
    
    proposed_actions = ActionMeasure.objects.filter(status=Measure.PROPOSED)
    for action in proposed_actions:
        for rule in RuleMeasure.objects.filter(status=Measure.PASSED, community_integration=action.community_integration):
            exec(rule.rule_code)
