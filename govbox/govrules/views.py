from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
import urllib.request
import urllib.parse

# Create your views here.

def submit_proposal(request):
    print(request)
    return HttpResponseRedirect('/')


def execute_proposal(proposal):
    from govrules.models import Proposal
    community_integration = proposal.community.community_integration
    
    obj = proposal.content_object
    call = community_integration.API + obj.API_METHOD
    
    print(obj)
    
    data = urllib.parse.urlencode({'token': community_integration.token,
                                   'name': obj.name,
                                   'description': obj.description}).encode('ascii')

    response = urllib.request.urlopen(url=call, data=data)
    
    html = response.read()
    print(html)
    
    print(call)
