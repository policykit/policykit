from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from redditintegration.models import RedditCommunity, RedditUser, REDDIT_USER_AGENT
from urllib import parse
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)

class RedditBackend(BaseBackend):

    def authenticate(self, request, oauth=None, platform=None):
        if not oauth:
            return None
        
        if platform != 'reddit':
            return None
        
        req = urllib.request.Request('https://oauth.reddit.com/subreddits/mine/subscriber')
        req.add_header('Authorization', 'bearer %s' % oauth['access_token'])
        req.add_header("User-Agent", REDDIT_USER_AGENT)
        resp = urllib.request.urlopen(req)
        reddit_info = json.loads(resp.read().decode('utf-8'))
        
        logger.info(reddit_info)
        community = None
        
        for item in reddit_info['data']['children']:
            if item['data']['title'] != '':
                title = item['data']['display_name']
        
                s = RedditCommunity.objects.filter(team_id=title)
                if s.exists():
                    community = s[0]

        if community:

            req = urllib.request.Request('https://oauth.reddit.com/api/v1/me')
            req.add_header('Authorization', 'bearer %s' % oauth['access_token'])
            req.add_header("User-Agent", REDDIT_USER_AGENT)
            resp = urllib.request.urlopen(req)
            user_info = json.loads(resp.read().decode('utf-8'))
            
            logger.info(user_info)
            
            
#             slack_user = SlackUser.objects.filter(username=oauth['authed_user']['id'])
#             
#             if slack_user.exists() and slack_user[0].readable_name != None:
#                 # update user info
#                 slack_user = slack_user[0]
#                 slack_user.access_token = oauth['authed_user']['access_token']
#                 slack_user.community = s[0]
#                 slack_user.password = oauth['authed_user']['access_token']
#                 slack_user.save()
#             
#             
# 
#             
#             else:
#                 
#                 
#                 user_req = urllib.request.Request('https://slack.com/api/users.identity?', data=user_data)
#                 user_resp = urllib.request.urlopen(user_req)
#                 user_res = json.loads(user_resp.read().decode('utf-8'))
# 
# 
#                 if slack_user.exists():
#                     slack_user = slack_user[0]
#                     slack_user.access_token = oauth['authed_user']['access_token']
#                     slack_user.community = s[0]
#                     slack_user.password = oauth['authed_user']['access_token']
#                     slack_user.readable_name = user_res['user']['name']
#                     slack_user.avatar = user_res['user']['image_24']
#                     slack_user.save()
#                 else:
#                     slack_user,_ = SlackUser.objects.get_or_create(
#                         username=oauth['authed_user']['id'],
#                         password=oauth['authed_user']['access_token'],
#                         community = s[0],
#                         readable_name = user_res['user']['name'],
#                         avatar = user_res['user']['image_24'],
#                         access_token = oauth['authed_user']['access_token'],
#                         )
#             return slack_user
        return None


    def get_user(self, user_id):
        try:
            return RedditUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
