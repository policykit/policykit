from django.test import TestCase, override_settings
from policyengine.models import Community, CommunityPlatform, CommunityUser, CommunityRole
from integrations.discord.models import DiscordCommunity
from integrations.slack.models import SlackCommunity
from constitution.models import ConstitutionCommunity
import policyengine.utils as Utils

import os
import json


class InitStarterKitTests(TestCase):
    def test_initialize_starterkit(self):
        """Test that starter kit initializion for all kits on all platforms doesn't throw any errors"""
        starterkits_info = Utils.get_starterkits_info()
        cur_path = os.path.abspath(os.path.dirname(__file__))
        all_kits = []
        for k in starterkits_info:
            starter_kit_path = os.path.join(cur_path, f"../starterkits/{k['id']}.json")
            f = open(starter_kit_path)
            all_kits.append(json.loads(f.read()))
            f.close()

        for platform in ["slack", "discord", "reddit", "discourse"]:
            for kit_data in all_kits:
                # print(f"Initializing kit '{kit_data['name']}' for {platform}")
                community_platform = self._new_platform_community(platform)
                Utils.initialize_starterkit_inner(community_platform.community, kit_data, creator_username="xyz")
                roles = community_platform.community.get_roles()
                self.assertEqual(roles.filter(is_base_role=True).count(), 1)

    def _new_platform_community(self, platform):
        Community.objects.all().delete()

        # get the CommunityPlatform class
        cls = self._get_community_cls(platform)
        platform_community = cls.objects.create(
            community_name="my community",
            team_id="test",
        )

        # Create some users to test the roles
        CommunityUser.objects.create(username="user1", community=platform_community)
        CommunityUser.objects.create(username="user2", community=platform_community, is_community_admin=True)
        return platform_community

    def _get_community_cls(self, platform):
        from django.apps import apps

        for cls in apps.get_app_config(platform).get_models():
            if issubclass(cls, CommunityPlatform):
                return cls


class CommunityCreationTests(TestCase):
    def test_community_creation(self):
        """Create Community then create CommunityPlatform"""
        community = Community.objects.create()
        platform_community = DiscordCommunity.objects.create(
            community=community, community_name="my server", team_id=1234
        )

        self.assertEqual(community.community_name, "my server")
        self.assertEqual(community.constitution_community.community_name, "my server")
        self.assertEqual(community.get_platform_communities().count(), 1)
        self.assertEqual(community.get_platform_communities()[0], platform_community)

    def test_no_platform_community(self):
        """Create a community with no platform, just a constitution community"""
        constitution_community = ConstitutionCommunity.objects.create(community_name="my community")
        community = constitution_community.community

        self.assertEqual(community.community_name, "my community")
        self.assertEqual(community.constitution_community, constitution_community)
        self.assertEqual(community.get_platform_communities().count(), 0)

    def test_no_platform_community_reverts(self):
        """Create a community with no platform, just a constitution community"""
        community = Community.objects.create()
        constitution_community = ConstitutionCommunity.objects.create(
            community_name="my community", community=community
        )

        self.assertEqual(community.community_name, "my community")
        self.assertEqual(community.constitution_community, constitution_community)
        self.assertEqual(community.get_platform_communities().count(), 0)

    def test_secondary_community_creation(self):
        """Community with two platforms"""

        discord = DiscordCommunity.objects.create(community_name="my server", team_id=1234)
        community = discord.community

        self.assertEqual(community.community_name, "my server")
        self.assertEqual(community.constitution_community.community_name, "my server")
        self.assertEqual(community.get_platform_communities().count(), 1)
        self.assertEqual(community.get_platform_communities()[0], discord)

        slack = SlackCommunity.objects.create(community_name="my org", team_id="abcd", community=community)

        self.assertEqual(community.get_platform_communities().count(), 2)
        self.assertEqual(community.community_name, "my server")
        self.assertEqual(community.constitution_community.community_name, "my server")
        self.assertEqual(ConstitutionCommunity.objects.all().count(), 1)
