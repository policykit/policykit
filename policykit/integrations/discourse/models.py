from django.db import models
from policyengine.models import CommunityPlatform, CommunityUser, PlatformAction, StarterKit, ConstitutionPolicy, Proposal, PlatformPolicy, CommunityRole
from django.contrib.auth.models import Permission, ContentType, User
import urllib
from urllib import parse
import urllib.request
import base64
import json
import logging

logger = logging.getLogger(__name__)

DISCOURSE_ACTIONS = [
                    'discoursecreatetopic',
                    'discoursecreatepost'
                  ]

DISCOURSE_VIEW_PERMS = ['Can view discourse create topic', 'Can view discourse create post']

DISCOURSE_PROPOSE_PERMS = ['Can add discourse create topic', 'Can add discourse create post']

DISCOURSE_EXECUTE_PERMS = ['Can execute discourse create topic', 'Can execute discourse create post']

class DiscourseCommunity(CommunityPlatform):
    platform = "discourse"

    team_id = models.CharField('team_id', max_length=150, unique=True)
    api_key = models.CharField('api_key', max_length=100, unique=True)

    def initiate_vote(self, action, policy, users=None, template=None, topic_id=None):
        from integrations.discourse.views import initiate_action_vote
        initiate_action_vote(policy, action, users, template, topic_id)

    def post_message(self, text, topic_id):
        # TODO: update this method to support commenting on an existing topic,
        # sending DM, sending multi-person message, etc. Metagov Discourse supports this.
        data = {'raw': text, 'topic_id': topic_id}
        return self.make_call('/posts.json', values=data)

    def save(self, *args, **kwargs):
        super(DiscourseCommunity, self).save(*args, **kwargs)

        content_types = ContentType.objects.filter(model__in=DISCOURSE_ACTIONS)
        perms = Permission.objects.filter(content_type__in=content_types, name__contains="can add ")
        for p in perms:
            self.base_role.permissions.add(p)

    def make_call(self, url, values=None, action=None, method=None):
        data = None
        if values:
            data = urllib.parse.urlencode(values)
            data = data.encode('utf-8')

        req = urllib.request.Request(self.team_id + url, data, method=method)
        req.add_header('User-Api-Key', self.api_key)

        try:
            resp = urllib.request.urlopen(req)
        except urllib.error.HTTPError as e:
            logger.error('reached HTTPError')
            logger.error(e.code)
            error_message = e.read()
            logger.error(error_message)
            raise

        resp_body = resp.read().decode('utf-8')
        if resp_body:
            return json.loads(resp_body)
        return None

    def execute_platform_action(self, action, delete_policykit_post=True):
        from policyengine.models import LogAPICall, CommunityUser
        from policyengine.views import clean_up_proposals

        obj = action

        if not obj.community_origin or (obj.community_origin and obj.community_revert):
            call = obj.ACTION

            obj_fields = []
            for f in obj._meta.get_fields():
                if f.name not in ['polymorphic_ctype',
                                  'community',
                                  'initiator',
                                  'communityapi_ptr',
                                  'platformaction',
                                  'platformactionbundle',
                                  'community_revert',
                                  'community_origin',
                                  'is_bundled'
                                  ]:
                    obj_fields.append(f.name)

            data = {}

            for item in obj_fields:
                try:
                    if item != 'id':
                        value = getattr(obj, item)
                        data[item] = value
                except obj.DoesNotExist:
                    continue

            res = LogAPICall.make_api_call(self, data, call)

            if delete_policykit_post:
                posted_action = None
                if action.is_bundled:
                    bundle = action.platformactionbundle_set.all()
                    if bundle.exists():
                        posted_action = bundle[0]
                else:
                    posted_action = action

                if posted_action.community_post:
                    data = {}
                    call = 'posts/{0}.json'.format(posted_action.community_post)
                    _ = LogAPICall.make_api_call(self, data, call)

            if res['ok']:
                clean_up_proposals(action, True)
            else:
                error_message = res['error']
                logger.info(error_message)
                clean_up_proposals(action, False)
        else:
            clean_up_proposals(action, True)

class DiscourseUser(CommunityUser):
    def save(self, *args, **kwargs):
        super(DiscourseUser, self).save(*args, **kwargs)
        group = self.community.base_role
        group.user_set.add(self)

class DiscourseCreateTopic(PlatformAction):
    title = models.TextField()
    raw = models.TextField()
    topic_id = models.IntegerField()
    category = models.IntegerField()

    ACTION = 'posts.json'
    AUTH = 'user'

    action_codename = 'discoursecreatetopic'
    app_name = 'discourseintegration'
    action_type = "DiscourseCreateTopic"

    class Meta:
        permissions = (
            ('can_execute_discoursecreatetopic', 'Can execute discourse create topic'),
        )

    def revert(self):
        values = {}
        call = f"/t/{self.topic_id}.json"
        super().revert(values, call, method='DELETE')

    def execute(self):
        # Execute action if it didnt originate in the community
        if not self.community_origin:
            topic = self.community.make_call('/posts.json', {'title': self.title, 'raw': self.raw, 'category': self.category})

            self.topic_id = topic['id']
            self.save()

        # Execute action if it was previously reverted
        if self.community_origin and self.community_revert:
            # Recover topic rather than re-creating because otherwise Discourse
            # will flag re-created topic as repetitive post and fail it with
            # a 422 error: "Title has already been used".
            self.community.make_call(f"/t/{self.topic_id}/recover", method='PUT')
            self.community_revert = False

class DiscourseCreatePost(PlatformAction):
    raw = models.TextField()
    post_id = models.IntegerField()

    ACTION = 'posts.json'
    AUTH = 'user'

    action_codename = 'discoursecreatepost'
    app_name = 'discourseintegration'
    action_type = "DiscourseCreatePost"

    class Meta:
        permissions = (
            ('can_execute_discoursecreatepost', 'Can execute discourse create post'),
        )

    def revert(self):
        values = {}
        call = f"/posts/{self.post_id}.json"
        super().revert(values, call, method='DELETE')

    def execute(self):
        # only execute the action if it didnt originate in the community, OR if it was previously reverted
        if not self.community_origin or (self.community_origin and self.community_revert):
            reply = self.community.make_call('/posts.json', {'raw': self.raw}) #FIXME this needs to have topic_id
            self.post_id = reply['id']
            self.save()

class DiscourseStarterKit(StarterKit):
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
                c.name = "Discourse: " + community.community_name + ": " + role.role_name
                c.description = role.description
                c.save()

            for perm in role.permissions.all():
                c.permissions.add(perm)

            jsonDec = json.decoder.JSONDecoder()
            perm_set = jsonDec.decode(role.plat_perm_set)

            if 'view' in perm_set:
                for perm in DISCOURSE_VIEW_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)
            if 'propose' in perm_set:
                for perm in DISCOURSE_PROPOSE_PERMS:
                    p1 = Permission.objects.get(name=perm)
                    c.permissions.add(p1)
            if 'execute' in perm_set:
                for perm in DISCOURSE_EXECUTE_PERMS:
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
