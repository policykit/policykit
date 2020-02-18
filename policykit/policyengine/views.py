from django.shortcuts import render
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect, HttpResponse
import urllib.request
import urllib.parse
import logging
import json

logger = logging.getLogger(__name__)


def execute_action(action):
    logger.info('here')
    logger.info('EXECUTING ACTION BELOW:')
    logger.info(action)
    
    community_integration = action.community_integration
    
    obj = action.content_object
    call = community_integration.API + obj.ACTION
    
    logger.info(call)

    
    obj_fields = []
    for f in obj._meta.get_fields():
        if f.name not in ['polymorphic_ctype','community_integration','author','communityaction_ptr']:
            obj_fields.append(f.name) 
    
    data = {}
    
    if obj.AUTH == "user":
        data['token'] = action.author.access_token
    else:
        data['token'] = community_integration.access_token
    
    logger.info('here2')
    
    for item in obj_fields:
        try :
            if item != 'id':
                value = getattr(obj, item)
                data[item] = value
        except obj.DoesNotExist:
            continue
    
    data = urllib.parse.urlencode(data).encode('ascii')
    
    logger.info(data)

    response = urllib.request.urlopen(url=call, data=data)
    
    html = response.read()
    
    logger.info(html)
    
    res = json.loads(html)
    
    
    if obj.community_post_id:
        values = {'token': action.author.access_token,
                  'ts': obj.community_post_id,
                  'channel': obj.channel
                }
        data = urllib.parse.urlencode(values)
        data = data.encode('utf-8')
        call_info = community_integration.API + 'chat.delete?'
        req = urllib.request.Request(call_info, data)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        logger.info(res)
    
    
    
    if res['ok']:
        from policyengine.models import Policy
        action.status = Policy.PASSED
        action.save()
    else:
        error_message = res['error']
        logger.info(error_message)
    
