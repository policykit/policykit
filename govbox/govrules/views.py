from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
import urllib.request
import urllib.parse

# Create your views here.






def execute_proposal(proposal):
    from govrules.models import Proposal
    community_integration = proposal.community.community_integration
    
    if proposal.action == Proposal.ADD and proposal.content_type == ContentType.objects.get(model="slackusergroup"):
        call = community_integration.API + 'usergroups.create'
        
        obj = proposal.content_object
        print(obj)
        
        data = urllib.parse.urlencode({'token': community_integration.token,
                                       'name': obj.name,
                                       'description': obj.description}).encode('ascii')

        response = urllib.request.urlopen(url=call, data=data)
        
        html = response.read()
        print(html)
        
        print(call)
