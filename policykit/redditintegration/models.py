from django.db import models
from policyengine.models import Community, CommunityUser, PlatformAction, StarterKit, ConstitutionPolicy, Proposal, PlatformPolicy, CommunityRole
from django.contrib.auth.models import Permission, ContentType, User
from policykit.settings import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
import urllib
from urllib import parse
import base64
import json
import logging

logger = logging.getLogger(__name__)


REDDIT_USER_AGENT = 'PolicyKit:v1.0 (by /u/axz1919)'

REDDIT_ACTIONS = ['redditmakepost']

REDDIT_VIEW_PERMS = ['Can view reddit make post']

REDDIT_PROPOSE_PERMS = ['Can add reddit make post']

REDDIT_EXECUTE_PERMS = ['Can execute reddit make post']

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


class RedditCommunity(Community):
    API = 'https://oauth.reddit.com/'

    platform = "reddit"

    team_id = models.CharField('team_id', max_length=150, unique=True)

    access_token = models.CharField('access_token',
                                    max_length=300,
                                    unique=True)

    refresh_token = models.CharField('refresh_token',
                               max_length=500,
                               null=True)


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

    def notify_action(self, action, policy, users=None):
        from redditintegration.views import post_policy
        post_policy(policy, action, users)


    def execute_platform_action(self, action, delete_policykit_post=True):
        from policyengine.models import LogAPICall, CommunityUser
        from policyengine.views import clean_up_proposals

        logger.info('here')

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
                                  'platformaction',
                                  'platformactionbundle',
                                  'community_revert',
                                  'community_origin',
                                  'is_bundled',
                                  'proposal',
                                  'data',
                                  'community_post',
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
                posted_action = None
                if action.is_bundled:
                    bundle = action.platformactionbundle_set.all()
                    if bundle.exists():
                        posted_action = bundle[0]
                else:
                    posted_action = action

                if posted_action.community_post:
                    values = {'id': posted_action.community_post
                            }
                    call = 'api/remove'
                    _ = LogAPICall.make_api_call(self, values, call)

            # approve post
            logger.info('approve executed post')
            action.community.make_call('api/approve', {'id': res['json']['data']['name']})

        clean_up_proposals(action, True)


class RedditUser(CommunityUser):
    refresh_token = models.CharField('refresh_token',
                               max_length=500,
                               null=True)

    avatar = models.CharField('avatar',
                           max_length=500,
                           null=True)

    def refresh_access_token(self):
        res = refresh_access_token(self.refresh_token)
        self.access_token = res['access_token']
        self.save()


class RedditMakePost(PlatformAction):
    ACTION = 'api/submit'
    AUTH = 'user'

    title = models.CharField('title',
                               max_length=500,
                               null=True)
    text = models.TextField()

    kind = models.CharField('kind',
                               max_length=30,
                               default="self")

    name = models.CharField('name',
                               max_length=100,
                               null=True)
    communityaction_ptr = models.CharField('ptr',
                               max_length=100,
                               null=True)

    action_codename = 'redditmakepost'

    app_name = 'redditintegration'

    action_type = "RedditMakePost"

    class Meta:
        permissions = (
            ('can_execute_redditmakepost', 'Can execute reddit make post'),
        )


    def revert(self):
        values = {'id': self.name
                }
        super().revert(values, 'api/remove')

    def execute(self):
        if not self.community_revert:
            self.community.make_call('api/approve', {'id': self.name})
        super().execute()

class RedditStarterKit(StarterKit):
    def init_kit(self, community, creator_token=None):
        for policy in self.genericpolicy_set.all():
            if policy.is_constitution:
                p = ConstitutionPolicy()
                p.community = community
                p.filter = policy.filter
                p.initialize = policy.initialize
                p.check = policy.check
                p.notify = policy.notify
                p.success = policy.success
                p.fail = policy.fail
                p.description = policy.description
                p.name = policy.name
                
                proposal = Proposal.objects.create(author=None, status=Proposal.PASSED)
                p.proposal = proposal
                p.save()
            
            else:
                p = PlatformPolicy()
                p.community = community
                p.filter = policy.filter
                p.initialize = policy.initialize
                p.check = policy.check
                p.notify = policy.notify
                p.success = policy.success
                p.fail = policy.fail
                p.description = policy.description
                p.name = policy.name
                
                proposal = Proposal.objects.create(author=None, status=Proposal.PASSED)
                p.proposal = proposal
                p.save()
    
        for role in self.genericrole_set.all():
            c = None
            if role.is_base_role:
                c = community.base_role
                role.is_base_role = False
            else:
                c = CommunityRole()
                c.community = community
                c.role_name = role.role_name
                c.name = "Reddit: " + community.community_name + ": " + role.role_name
                c.save()
                
            for perm in role.permissions.all():
                c.permissions.add(perm)
            
            jsonDec = json.decoder.JSONDecoder()
            perm_set = jsonDec.decode(role.plat_perm_set)
            
            if 'view' in perm_set:
                for perm in REDDIT_VIEW_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)
            elif 'propose' in perm_set:
                for perm in REDDIT_PROPOSE_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)
            elif 'execute' in perm_set:
                for perm in REDDIT_EXECUTE_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)
            
            if role.user_group == "admins":
                group = CommunityUser.objects.filter(community = community, is_community_admin = True)
                for user in group:
                    c.user_set.add(user)
            elif role.user_group == "nonadmins":
                group = CommunityUser.objects.filter(community = community, is_community_admin = False)
                for user in group:
                    c.user_set.add(user)
            elif role.user_group == "all":
                group = CommunityUser.objects.filter(community = community)
                for user in group:
                    c.user_set.add(user)
            elif role.user_group == "creator":
                user = CommunityUser.objects.get(access_token=creator_token)
                c.user_set.add(user)

            c.save()
