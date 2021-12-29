from django.db import models
from policyengine.models import CommunityPlatform, CommunityUser, GovernableAction, Proposal
from policykit.settings import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
import urllib
from urllib import parse
import base64
import json
import logging

logger = logging.getLogger(__name__)

REDDIT_USER_AGENT = 'PolicyKit:v1.0 (by /u/axz1919)'


def refresh_access_token(refresh_token):
    data = parse.urlencode({
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
        }).encode()

    req = urllib.request.Request('https://www.reddit.com/api/v1/access_token', data=data)

    credentials = ('%s:%s' % (REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET))
    encoded_credentials = base64.b64encode(credentials.encode('ascii'))

    req.add_header("Authorization", "Basic %s" % encoded_credentials.decode("ascii"))
    req.add_header("User-Agent", "PolicyKit-App-Reddit-Integration v 1.0")

    resp = urllib.request.urlopen(req)
    res = json.loads(resp.read().decode('utf-8'))
    return res

class RedditCommunity(CommunityPlatform):
    API = 'https://oauth.reddit.com/'
    platform = "reddit"

    team_id = models.CharField('team_id', max_length=150, unique=True)
    access_token = models.CharField('access_token', max_length=300, unique=True)
    refresh_token = models.CharField('refresh_token', max_length=500, null=True)

    def make_call(self, url, values=None, action=None, method=None):
        logger.info(self.API + url)

        if values:
            data = urllib.parse.urlencode(values)
            data = data.encode('utf-8')
            logger.info(data)
        else:
            data = None

        try:
            user_token = False
            req = urllib.request.Request(self.API + url, data)

            if action and action.AUTH == 'user':
                user = action.initiator
                if user.access_token:
                    req.add_header('Authorization', 'bearer %s' % user.access_token)
                    user_token = True
                else:
                    req.add_header('Authorization', 'bearer %s' % self.access_token)
            else:
                req.add_header('Authorization', 'bearer %s' % self.access_token)
            req.add_header("User-Agent", REDDIT_USER_AGENT)

            logger.info(req.headers)
            resp = urllib.request.urlopen(req)
            res = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.reason == 'Unauthorized':

                if user_token:
                    ruser = user.reddituser
                    ruser.refresh_access_token()
                else:
                    self.refresh_access_token()

                req = urllib.request.Request(self.API + url, data)
                if action and action.AUTH == 'user':
                    user = action.initiator
                    req.add_header('Authorization', 'bearer %s' % user.access_token)
                else:
                    req.add_header('Authorization', 'bearer %s' % self.access_token)
                req.add_header("User-Agent", REDDIT_USER_AGENT)
                resp = urllib.request.urlopen(req)
                res = json.loads(resp.read().decode('utf-8'))
            else:
                logger.info(e)
        return res

    def refresh_access_token(self):
        res = refresh_access_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()

    def initiate_vote(self, proposal, users=None):
        from redditintegration.views import initiate_action_vote
        initiate_action_vote(proposal, users)

    def _execute_platform_action(self, action, delete_policykit_post=True):
        from policyengine.models import LogAPICall

        logger.info(action)

        obj = action

        if not obj.community_origin or (obj.community_origin and obj.community_revert):
            logger.info('EXECUTING ACTION BELOW:')
            call = obj.ACTION
            logger.info(call)

            obj_fields = []
            for f in obj._meta.get_fields():
                if f.name not in ['polymorphic_ctype',
                                  'community',
                                  'initiator',
                                  'communityaction_ptr',
                                  'governableaction',
                                  'community_revert',
                                  'community_origin',
                                  'is_bundled',
                                  'data',
                                  'vote_post_id',
                                  'name'
                                  ]:
                    obj_fields.append(f.name)

            data = {}

            for item in obj_fields:
                try :
                    if item != 'id':
                        value = getattr(obj, item)
                        data[item] = value
                except obj.DoesNotExist:
                    continue

            data['sr'] = action.community.community_name
            data['api_type'] = 'json'

            res = LogAPICall.make_api_call(self, data, call, action=action)

            logger.info(res)

            # delete PolicyKit Post
            logger.info('delete policykit post')
            if delete_policykit_post:
                for e in Proposal.objects.filter(action=action):
                    if e.vote_post_id:
                        values = {'id': e.vote_post_id}
                        call = 'api/remove'
                        _ = LogAPICall.make_api_call(self, values, call)

            # approve post
            logger.info('approve executed post')
            action.community.make_call('api/approve', {'id': res['json']['data']['name']})


class RedditUser(CommunityUser):
    refresh_token = models.CharField('refresh_token', max_length=500, null=True)

    def refresh_access_token(self):
        res = refresh_access_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()

class RedditMakePost(GovernableAction):
    ACTION = 'api/submit'
    AUTH = 'user'

    title = models.CharField('title', max_length=500, null=True)
    text = models.TextField()
    kind = models.CharField('kind', max_length=30, default="self")
    name = models.CharField('name', max_length=100, null=True)
    communityaction_ptr = models.CharField('ptr', max_length=100, null=True)

    class Meta:
        permissions = (
            ('can_execute_redditmakepost', 'Can execute reddit make post'),
        )

    def revert(self):
        values = {'id': self.name}
        super().revert(values=values, call='api/remove')

    def execute(self):
        if not self.community_revert:
            self.community.make_call('api/approve', {'id': self.name})
        super().execute()
