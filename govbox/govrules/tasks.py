# Create your tasks here
from __future__ import absolute_import, unicode_literals

from celery import shared_task
from celery.schedules import crontab
from govrules.models import UserVote
from govbox.celery import app


@shared_task
def count_votes():
    return UserVote.objects.count()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Calls test('hello') every 50 seconds.
    sender.add_periodic_task(50.0, test.s('hello'), name='add every 50')

    # Calls test('world') every 100 seconds
    sender.add_periodic_task(100.0, test.s('world'), expires=10)

    # Executes every Monday morning at 7:30 a.m.
    sender.add_periodic_task(
        crontab(hour=7, minute=30, day_of_week=1),
        test.s('Happy Mondays!'),
    )

@app.task
def test(arg):
    print(arg)