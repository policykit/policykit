# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from govrules.models import UserVote, ActionPolicy, Policy, RulePolicy, CommunityUser
from govbox.celery import app
from govrules.views import *

@shared_task
def consider_proposed_actions():
    
    proposed_actions = ActionPolicy.objects.filter(status=Policy.PROPOSED)
    for action in proposed_actions:
        for rule in RulePolicy.objects.filter(status=Policy.PASSED, community_integration=action.community_integration):
            exec(rule.rule_code)
