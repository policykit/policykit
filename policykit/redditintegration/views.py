from django.shortcuts import render
from django.http import HttpResponse
from policykit.settings import REDDIT_CLIENT_SECRET
from django.shortcuts import redirect
from redditintegration.models import RedditCommunity, RedditUser
from policyengine.models import *
from django.views.decorators.csrf import csrf_exempt
from urllib import parse
import urllib.request
import json
import base64
import logging

logger = logging.getLogger(__name__)


# Create your views here.

def oauth(request):
    logger.info(request)
    
    state = request.GET.get('state')
    if state == "policykit_reddit_string":
        
        code = request.GET.get('code')
        
        logger.info(code)
        
        data = parse.urlencode({
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': 'https://policykit.org/reddit/oauth',
            }).encode()
            
        req = urllib.request.Request('https://www.reddit.com/api/v1/access_token', data=data)
        
        credentials = ('%s:%s' % ('QrZzzkLgVc1x6w', REDDIT_CLIENT_SECRET))
        encoded_credentials = base64.b64encode(credentials.encode('ascii'))

        req.add_header("Authorization", "Basic %s" % encoded_credentials.decode("ascii"))
        req.add_header("User-Agent", "PolicyKit-App-Reddit-Integration v 1.0")

        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        
        logger.info(res)
        
        s = RedditCommunity.objects.filter(team_id=res['team']['id'])
            community = None
            user_group,_ = CommunityRole.objects.get_or_create(name="Base User")
            if not s.exists():
                community = SlackCommunity.objects.create(
                    community_name=res['team']['name'],
                    team_id=res['team']['id'],
                    access_token=res['access_token'],
                    base_role=user_group
                    )
                user_group.community = community
                user_group.save()
                
                cg = CommunityDoc.objects.create(text='',
                                                 community=community)
                
                
                community.community_guidelines=cg
                community.save()
                
            else:
                s[0].community_name = res['team']['name']
                s[0].team_id = res['team']['id']
                s[0].access_token = res['access_token']
                s[0].save()
                community = s[0]
            
            user = SlackUser.objects.filter(username=res['authed_user']['id'])
            if not user.exists():
                
                # CHECK HERE THAT USER IS ADMIN
                
                _ = SlackUser.objects.create(username=res['authed_user']['id'],
                                             access_token=res['authed_user']['access_token'],
                                             is_community_admin=True,
                                             community=community
                                             )
        
        
        
        
        
        
    
        response = redirect('/login?success=true')
        return response
    
    response = redirect('/login?success=false')
    return response



@csrf_exempt
def action(request):
    json_data = json.loads(request.body)
    logger.info('RECEIVED ACTION')
    logger.info(json_data)
    
    
def post_policy():
    pass
