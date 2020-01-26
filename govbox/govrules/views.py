from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
import urllib.request
import urllib.parse
import logging
import json

logger = logging.getLogger(__name__)


def execute_action(action):
    
    try:
    
        logger.info('here')
        
        community_integration = action.community_integration
        
        obj = action.content_object
        call = community_integration.API + obj.ACTION
        
        
        obj_fields = []
        for f in obj._meta.get_fields():
            if f.name not in ['polymorphic_ctype','community_integration','author','communityaction_ptr']:
                obj_fields.append(f.name) 
        
        data = {}
        
        if obj.AUTH == "user":
            data['token'] = action.author.access_token
        else:
            data['token'] = community_integration.access_token
        
        for item in obj_fields:
            try :
                if item != 'id':
                    value = getattr(obj, item)
                    data[item] = value
            except obj.DoesNotExist:
                continue
        
        data = urllib.parse.urlencode(data).encode('ascii')
    
        response = urllib.request.urlopen(url=call, data=data)
        
        logger.info(call)
        logger.info(data)
        
        html = response.read()
        
        logger.info(html)
        
        res = json.loads(html)
        
        
        
        if res['ok']:
            from govrules.models import Measure
            action.status = Measure.PASSED
            action.save()
        else:
            error_message = res['error']
        
    except Exception as e:
        logger.error(e)
