from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
import urllib.request
import urllib.parse
import logging

logger = logging.getLogger(__name__)


def execute_action(action):
    community_integration = action.community_integration
    
    obj = action.content_object
    call = community_integration.API + obj.API_METHOD
    
    print(obj)
    
    data = urllib.parse.urlencode({'token': community_integration.access_token,
                                   'text': obj.message,
                                   'channel': obj.channel}).encode('ascii')

    response = urllib.request.urlopen(url=call, data=data)
    
    html = response.read()
    print(html)
    
    print(call)
