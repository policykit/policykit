from django.db import models
from policyengine.models import CommunityPlatform, CommunityUser, GovernableAction, Proposal
import urllib
import urllib.request
import json
import logging

logger = logging.getLogger(__name__)


class DiscourseCommunity(CommunityPlatform):
    platform = "discourse"

    team_id = models.CharField('team_id', max_length=150, unique=True)
    api_key = models.CharField('api_key', max_length=100, unique=True)

    def initiate_vote(self, proposal, users=None, text=None, topic_id=None):
        from integrations.discourse.views import initiate_action_vote
        initiate_action_vote(proposal, users, text, topic_id)

    def post_message(self, proposal, text, topic_id):
        # TODO: update this method to support commenting on an existing topic,
        # sending DM, sending multi-person message, etc. Metagov Discourse supports this.
        data = {'raw': text, 'topic_id': topic_id}
        return self.make_call('/posts.json', values=data)

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

    def _execute_platform_action(self, action, delete_policykit_post=True):
        from policyengine.models import LogAPICall

        obj = action

        if not obj.community_origin or (obj.community_origin and obj.community_revert):
            call = obj.ACTION

            obj_fields = []
            for f in obj._meta.get_fields():
                if f.name not in ['polymorphic_ctype',
                                  'community',
                                  'initiator',
                                  'communityapi_ptr',
                                  'governableaction',
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
                for e in Proposal.objects.filter(action=action):
                    if e.vote_post_id:
                        data = {}
                        call = 'posts/{0}.json'.format(e.vote_post_id)
                        _ = LogAPICall.make_api_call(self, data, call)

            if not res['ok']:
                error_message = res['error']
                logger.info(error_message)

class DiscourseUser(CommunityUser):
    pass

class DiscourseCreateTopic(GovernableAction):
    title = models.TextField()
    raw = models.TextField()
    topic_id = models.IntegerField()
    category = models.IntegerField()

    ACTION = 'posts.json'
    AUTH = 'user'

    class Meta:
        permissions = (
            ('can_execute_discoursecreatetopic', 'Can execute discourse create topic'),
        )

    def revert(self):
        values = {}
        call = f"/t/{self.topic_id}.json"
        super().revert(values=values, call=call, method='DELETE')

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

class DiscourseCreatePost(GovernableAction):
    raw = models.TextField()
    post_id = models.IntegerField()

    ACTION = 'posts.json'
    AUTH = 'user'

    class Meta:
        permissions = (
            ('can_execute_discoursecreatepost', 'Can execute discourse create post'),
        )

    def revert(self):
        values = {}
        call = f"/posts/{self.post_id}.json"
        super().revert(value=values, call=call, method='DELETE')

    def execute(self):
        # only execute the action if it didnt originate in the community, OR if it was previously reverted
        if not self.community_origin or (self.community_origin and self.community_revert):
            reply = self.community.make_call('/posts.json', {'raw': self.raw}) #FIXME this needs to have topic_id
            self.post_id = reply['id']
            self.save()
