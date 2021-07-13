"""
Helper script for initializing starter kits for PolicyKit.

Run with:

python manage.py shell
exec(open('scripts/starterkits.py').read())
"""

from django.contrib.auth.models import Permission
from integrations.discord.models import DiscordStarterKit
from integrations.discourse.models import DiscourseStarterKit
from integrations.reddit.models import RedditStarterKit
from integrations.slack.models import SlackStarterKit
from policyengine.models import *
import json
import os

def init_starter_kit(filename):
    logger.info(filename)
    f = open(f'{os.getcwd()}/scripts/starterkits/{filename}.txt')

    data = json.loads(f.read())

    ## TODO: Define platform names in platform models, not here
    platform_starter_kits = [
        SlackStarterKit(name=data['name'], platform="slack"),
        RedditStarterKit(name=data['name'], platform="reddit"),
        DiscordStarterKit(name=data['name'], platform="discord"),
        DiscourseStarterKit(name=data['name'], platform="discourse")
    ]

    for starter_kit in platform_starter_kits:
        starter_kit.save()

        for pp in data['platform_policies']:
            GenericPolicy.objects.create(
                starterkit=starter_kit,
                name=pp['name'],
                description=pp['description'],
                is_bundled=pp['is_bundled'],
                is_constitution=False,
                filter=pp['filter'],
                initialize=pp['initialize'],
                check=pp['check'],
                notify=pp['notify'],
                success=pp['success'],
                fail=pp['fail']
            )

        for cp in data['constitution_policies']:
            GenericPolicy.objects.create(
                starterkit=starter_kit,
                name=cp['name'],
                description=cp['description'],
                is_bundled=cp['is_bundled'],
                is_constitution=True,
                filter=cp['filter'],
                initialize=cp['initialize'],
                check=cp['check'],
                notify=cp['notify'],
                success=cp['success'],
                fail=cp['fail']
            )

        for role in data['roles']:
            r = GenericRole.objects.create(
                role_name=role['name'],
                name=f"{role['name']} {starter_kit.platform}",
                starterkit=starter_kit,
                is_base_role=role['is_base_role'],
                user_group=role['user_group']
            )

            r.plat_perm_set = json.dumps(role['permission_sets'])
            r.save()

            for perm in role['permissions']:
                p = Permission.objects.get(name=perm)
                r.permissions.add(p)

    f.close()

for starter_kit in ['testing', 'moderators', 'democracy', 'dictator', 'jury']:
    init_starter_kit(starter_kit)
