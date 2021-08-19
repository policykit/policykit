from django.test import TestCase, override_settings
from policyengine.models import Community, CommunityRole, Policy
from policyengine.utils import initialize_starterkit_inner

import os
import json


@override_settings(METAGOV_ENABLED=False, METAGOV_URL="")
class StarterKitTests(TestCase):
    def setUp(self):
        pass

    def test_initialize_starterkit(self):
        """Test that starter kit initializion for all kits on all platforms doesn't throw any errors"""
        cur_path = os.path.abspath(os.path.dirname(__file__))
        all_kits = []
        for k in ["testing", "democracy", "jury", "dictator", "moderators"]:
            starter_kit_path = os.path.join(cur_path, f"../starterkits/{k}.txt")
            f = open(starter_kit_path)
            all_kits.append(json.loads(f.read()))
            f.close()

        for kit_data in all_kits:
            for platform in ["slack", "discord", "reddit", "discourse"]:
                print(f"Initializing kit '{kit_data['name']}' for {platform}")
                community = self._new_platform_community(platform)
                initialize_starterkit_inner(community, kit_data)

    def _new_platform_community(self, platform):
        Community.objects.all().delete()
        CommunityRole.objects.all().delete()
        cls = self._get_community_cls(platform)
        cls.objects.all().delete()
        user_group, _ = CommunityRole.objects.get_or_create(role_name="fake role", name="fake role")
        community = Community.objects.create()
        return cls.objects.create(
            community_name="my test community",
            community=community,
            team_id="test",
            base_role=user_group,
        )

    def _get_community_cls(self, platform):
        from policyengine.models import CommunityPlatform
        from django.apps import apps

        for cls in apps.get_app_config(platform).get_models():
            if issubclass(cls, CommunityPlatform):
                return cls