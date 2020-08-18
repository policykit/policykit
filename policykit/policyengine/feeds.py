from django.contrib.syndication.views import Feed
from django.template.defaultfilters import truncatewords
from .models import Community, CommunityUser, PlatformAction, StarterKit, ConstitutionPolicy, Proposal, PlatformPolicy, CommunityRole
from django.urls import reverse



class LatestPostsFeed(Feed):
    link = ""
    description = "New actions"
    
    def items(self):
        return PlatformPolicy.objects.filter(community=user.community)
    
    def item_title(self, item):
        return item.title


