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

            reddit_user = RedditUser.objects.filter(username=user_info['name'])
             
            if reddit_user.exists():
                # update user info
                reddit_user = reddit_user[0]
                reddit_user.access_token = oauth['access_token']
                reddit_user.community = community
                reddit_user.password = oauth['access_token']
                reddit_user.readable_name = user_info['name']
                reddit_user.avatar = user_info['icon_img']
                reddit_user.save()
            else:
                reddit_user,_ = RedditUser.objects.get_or_create(
                    username=user_info['name'],
                    password=oauth['access_token'],
                    community = community,
                    readable_name = user_info['name'],
                    avatar = user_info['icon_img'],
                    access_token = oauth['access_token'],
                    )
            return reddit_user
        return None


    def get_user(self, user_id):
        try:
            return RedditUser.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
