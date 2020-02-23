# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from policyengine.models import UserVote, ActionPolicy, BasePolicy, CommunityPolicy, CommunityUser
from policykit.celery import app
from policyengine.views import *

@shared_task
def consider_proposed_actions():
    
    proposed_actions = ActionPolicy.objects.filter(status=BasePolicy.PROPOSED)
    for action in proposed_actions:
        for rule in CommunityPolicy.objects.filter(status=BasePolicy.PASSED, community_integration=action.community_integration):
            exec(rule.rule_code)
