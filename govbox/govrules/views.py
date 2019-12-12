from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
import urllib.request

# Create your views here.






def execute_proposal(proposal):
    from govrules.models import Proposal
    community_integration = proposal.community.community_integration
    
    print(proposal.action == Proposal.ADD)
    print(proposal.content_object)
    
    if proposal.action == Proposal.ADD and proposal.content_type == ContentType.objects.get(model="slackusergroup"):
        call = community_integration.API + 'usergroups.list?token=' + community_integration.token

        response = urllib.request.urlopen(call)
        
        html = response.read()
        print(html)
        
        print(call)
