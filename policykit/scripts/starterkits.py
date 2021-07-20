"""
Helper script for initializing starter kits for PolicyKit.

Run with:

python manage.py shell
exec(open('scripts/starterkits.py').read())
"""

from django.contrib.auth.models import Permission
from policyengine.models import StarterKit, GenericPolicy, GenericRole
import json
import os

def init_starter_kit(filename):
    print(f'Adding starter kit: {filename}')
    f = open(f'{os.getcwd()}/scripts/starterkits/{filename}.txt')

    data = json.loads(f.read())

    platform_starter_kits = []
    for platform in ["slack", "reddit", "discord", "discourse"]:
        starter_kit = StarterKit.objects.get_or_create(name=data['name'], platform=platform)[0]
        platform_starter_kits.append(starter_kit)

    for starter_kit in platform_starter_kits:
        for policy in data['platform_policies']:
            p = GenericPolicy.objects.filter(starterkit__id=starter_kit.id,
                                             name=policy['name'],
                                             is_constitution=False)
            if not p.exists():
                GenericPolicy.objects.create(
                    starterkit=starter_kit,
                    name=policy['name'],
                    description=policy['description'],
                    is_bundled=policy['is_bundled'],
                    is_constitution=False,
                    filter=policy['filter'],
                    initialize=policy['initialize'],
                    check=policy['check'],
                    notify=policy['notify'],
                    success=policy['success'],
                    fail=policy['fail']
                )

        for policy in data['constitution_policies']:
            p = GenericPolicy.objects.filter(starterkit__id=starter_kit.id,
                                             name=policy['name'],
                                             is_constitution=True)
            if not p.exists():
                GenericPolicy.objects.create(
                    starterkit=starter_kit,
                    name=policy['name'],
                    description=policy['description'],
                    is_bundled=policy['is_bundled'],
                    is_constitution=True,
                    filter=policy['filter'],
                    initialize=policy['initialize'],
                    check=policy['check'],
                    notify=policy['notify'],
                    success=policy['success'],
                    fail=policy['fail']
                )

        for role in data['roles']:
            p = GenericRole.objects.filter(starterkit__id=starter_kit.id,
                                           name=f"{role['name']}: {data['name']}: {starter_kit.platform}")
            if not p.exists():
                r = GenericRole.objects.create(
                    starterkit=starter_kit,
                    role_name=role['name'],
                    name=f"{role['name']}: {data['name']}: {starter_kit.platform}",
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
