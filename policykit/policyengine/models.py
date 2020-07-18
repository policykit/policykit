from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.govinterface.models import LogEntry
from polymorphic.models import PolymorphicModel
from django.core.exceptions import ValidationError
from policyengine.views import check_policy, filter_policy, initialize_policy, pass_policy, fail_policy, notify_policy
import urllib
import json

import logging


logger = logging.getLogger(__name__)

# Default values for code fields in editor
DEFAULT_FILTER = "# Replace this code with your custom Filter code\nreturn True\n\n"
DEFAULT_INITIALIZE = "# Replace this code with your custom Initialize code\npass\n\n"
DEFAULT_CHECK = "# Replace this code with your custom Check code\nreturn PASSED\n\n"
DEFAULT_NOTIFY = "# Replace this code with your custom Notify code\npass\n\n"
DEFAULT_SUCCESS = "# Replace this code with your custom Pass code\naction.execute()\n\n"
DEFAULT_FAIL = "# Replace this code with your custom Fail code\npass\n\n"

def on_transaction_commit(func):
    def inner(*args, **kwargs):
        transaction.on_commit(lambda: func(*args, **kwargs))

    return inner

class Community(PolymorphicModel):
    community_name = models.CharField('team_name',
                              max_length=1000)
    base_role = models.OneToOneField('CommunityRole',
                                     models.CASCADE,
                                     related_name='base_community')
    community_guidelines = models.OneToOneField('CommunityDoc',
                                     models.CASCADE,
                                     related_name='base_doc_community',
                                     null=True)

    def notify_action(self, action, policy, users):
        pass

    def save(self, *args, **kwargs):
        if not self.pk:
            super(Community, self).save(*args, **kwargs)

            # create Starter ConstitutionPolicy
            p = ConstitutionPolicy()
            p.community = self
            p.filter = "return True"
            p.initialize = "pass"
            p.check = "return PASSED"
            p.notify = "pass"
            p.success = "action.execute()"
            p.fail = "pass"
            p.description = "Starter Policy: all policies pass"
            p.name = "Starter name"

            proposal = Proposal.objects.create(author=None, status=Proposal.PASSED)
            p.proposal = proposal
            p.save()

            # starter permissions for usergroup
            p1 = Permission.objects.get(name='Can add boolean vote')
            p2 = Permission.objects.get(name='Can change boolean vote')
            p3 = Permission.objects.get(name='Can delete boolean vote')
            p4 = Permission.objects.get(name='Can view boolean vote')
            self.base_role.permissions.add(p1)
            self.base_role.permissions.add(p2)
            self.base_role.permissions.add(p3)
            self.base_role.permissions.add(p4)

            p1 = Permission.objects.get(name='Can add number vote')
            p2 = Permission.objects.get(name='Can change number vote')
            p3 = Permission.objects.get(name='Can delete number vote')
            p4 = Permission.objects.get(name='Can view number vote')
            self.base_role.permissions.add(p1)
            self.base_role.permissions.add(p2)
            self.base_role.permissions.add(p3)
            self.base_role.permissions.add(p4)

            p11 = Permission.objects.get(name='Can add communityactionbundle')
            self.base_role.permissions.add(p11)
            p12 = Permission.objects.get(name='Can add communitypolicybundle')
            self.base_role.permissions.add(p12)

            p11 = Permission.objects.get(name='Can add constitutionactionbundle')
            self.base_role.permissions.add(p11)
            p12 = Permission.objects.get(name='Can add constitutionpolicybundle')
            self.base_role.permissions.add(p12)

            p1 = Permission.objects.get(name='Can add policykit add role')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit delete role')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit add permission')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit remove permission')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit add user role')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit remove user role')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit change community policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit change constitution policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit remove community policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit remove constitution policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit add community policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit add constitution policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit change community doc')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can execute policykit remove constitution policy')
            self.base_role.permissions.add(p1)

        else:
            super(Community, self).save(*args, **kwargs)


class CommunityRole(Group):
    community = models.ForeignKey(Community, models.CASCADE, null=True)
    role_name = models.CharField('readable_name', max_length=300, null=True)

    class Meta:
        verbose_name = 'communityrole'
        verbose_name_plural = 'communityroles'

    def save(self, *args, **kwargs):
        super(CommunityRole, self).save(*args, **kwargs)

    def __str__(self):
        return self.community.community_name + ': ' + self.role_name


class CommunityUser(User, PolymorphicModel):
    readable_name = models.CharField('readable_name', max_length=300, null=True)
    community = models.ForeignKey(Community, models.CASCADE)
    access_token = models.CharField('access_token', max_length=300, null=True)
    is_community_admin = models.BooleanField(default=False)

    def __str__(self):
        return self.username + '@' + self.community.community_name


class CommunityDoc(models.Model):
    text = models.TextField()
    community = models.ForeignKey(Community, models.CASCADE)

    def change_text(self, text):
        self.text = text
        self.save()


class DataStore(models.Model):
    data_store = models.TextField()

    def _get_data_store(self):
        if self.data_store != '':
            return json.loads(self.data_store)
        else:
            return {}

    def _set_data_store(self, obj):
        self.data_store = json.dumps(obj)
        self.save()

    def get(self, key):
        obj = self._get_data_store()
        return obj.get(key, None)

    def set(self, key, value):
        obj = self._get_data_store()
        obj[key] = value
        self._set_data_store(obj)
        return True

    def remove(self, key):
        obj = self._get_data_store()
        res = obj.pop(key, None)
        self._set_data_store(obj)
        if not res:
            return False
        return True


class LogAPICall(models.Model):
    community = models.ForeignKey(Community, models.CASCADE)
    proposal_time = models.DateTimeField(auto_now_add=True)
    call_type = models.CharField('call_type', max_length=300)
    extra_info = models.TextField()

    @classmethod
    def make_api_call(cls, community, values, call, action=None):
        logger.info("COMMUNITY API CALL")
        _ = LogAPICall.objects.create(community=community,
                                      call_type=call,
                                      extra_info=json.dumps(values)
                                      )
        res = community.make_call(call, values=values, action=action)
        logger.info("COMMUNITY API RESPONSE")
        return res


class Proposal(models.Model):
    PROPOSED = 'proposed'
    FAILED = 'failed'
    PASSED = 'passed'
    STATUS = [
        (PROPOSED, 'proposed'),
        (FAILED, 'failed'),
        (PASSED, 'passed')
    ]

    author = models.ForeignKey(
        CommunityUser,
        models.CASCADE,
        verbose_name='author',
        blank=True,
        null=True
        )
    proposal_time = models.DateTimeField(auto_now_add=True)
    status = models.CharField(choices=STATUS, max_length=10)

    def get_yes_votes(self, users=None):
        return self.get_boolean_votes(True, users)

    def get_no_votes(self, users=None):
        return self.get_boolean_votes(False, users)

    def get_boolean_votes(self, value=False, users=None):
        if users:
            votes = BooleanVote.objects.filter(boolean_value=False, proposal=self, user__in=users)
        else:
            votes = BooleanVote.objects.filter(boolean_value=False, proposal=self)
        return votes

    def get_number_votes(self, value=0, users=None):
        if users:
            votes = NumberVote.objects.filter(number_value=value, proposal=self, user__in=users)
        else:
            votes = NumberVote.objects.filter(number_value=value, proposal=self)
        return votes

    def save(self, *args, **kwargs):
        if not self.pk:
            ds = DataStore.objects.create()
            self.data = ds
        super(Proposal, self).save(*args, **kwargs)


class BaseAction(models.Model):
    community = models.ForeignKey(Community, models.CASCADE, verbose_name='community')
    community_post = models.CharField('community_post', max_length=300, null=True)
    proposal = models.OneToOneField(Proposal, models.CASCADE)
    is_bundled = models.BooleanField(default=False)
    data = models.OneToOneField(DataStore,
        models.CASCADE,
        verbose_name='data',
        null=True
    )

    class Meta:
        abstract = True


class ConstitutionAction(BaseAction, PolymorphicModel):
    community = models.ForeignKey(Community, models.CASCADE)
    initiator = models.ForeignKey(CommunityUser, models.CASCADE, null=True)
    is_bundled = models.BooleanField(default=False)

    action_type = "ConstitutionAction"

    action_codename = ''

    class Meta:
        verbose_name = 'constitutionaction'
        verbose_name_plural = 'constitutionactions'

    def pass_action(self):
        proposal = self.proposal
        proposal.status = Proposal.PASSED
        proposal.save()

    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new

            #runs only if they have propose permission
            p = Proposal.objects.create(status=Proposal.PROPOSED,
                                                author=self.initiator)
            self.proposal = p
            super(ConstitutionAction, self).save(*args, **kwargs)

            if not self.is_bundled:
                action = self
                #if they have execute permission, skip all policies
                if action.initiator.has_perm('policyengine.can_execute_' + action.action_codename):
                    action.execute()
                else:
                    for policy in ConstitutionPolicy.objects.filter(community=self.community):
                      if filter_policy(policy, action):

                          initialize_policy(policy, action)

                          check_result = check_policy(policy, action)
                          if check_result == Proposal.PASSED:
                              pass_policy(policy, action)
                          elif check_result == Proposal.FAILED:
                              fail_policy(policy, action)
                          else:
                              notify_policy(policy, action)
        else:
            super(ConstitutionAction, self).save(*args, **kwargs)


class ConstitutionActionBundle(BaseAction):
    ELECTION = 'election'
    BUNDLE = 'bundle'
    BUNDLE_TYPE = [
        (ELECTION, 'election'),
        (BUNDLE, 'bundle')
    ]

    action_type = "ConstitutionActionBundle"

    bundled_actions = models.ManyToManyField(ConstitutionAction)
    bundle_type = models.CharField(choices=BUNDLE_TYPE, max_length=10)

    def execute(self):
        if self.bundle_type == ConstitutionActionBundle.BUNDLE:
            for action in self.bundled_actions.all():
                action.execute()
                action.pass_action()

    def pass_action(self):
        proposal = self.proposal
        proposal.status = Proposal.PASSED
        proposal.save()

    class Meta:
        verbose_name = 'constitutionactionbundle'
        verbose_name_plural = 'constitutionactionbundles'


@receiver(post_save, sender=ConstitutionActionBundle)
@on_transaction_commit
def after_constitutionaction_bundle_save(sender, instance, **kwargs):
    action = instance
    #if they have execute permission, skip all policies
    if action.initiator.has_perm('policyengine.can_execute_' + action.action_codename):
        action.execute()
    else:
        for policy in ConstitutionPolicy.objects.filter(community=action.community):
            if filter_policy(policy, action):

                initialize_policy(policy, action)

                check_result = check_policy(policy, action)
                if check_result == Proposal.PASSED:
                  pass_policy(policy, action)
                elif check_result == Proposal.FAILED:
                  fail_policy(policy, action)
                else:
                  notify_policy(policy, action)

class PolicykitChangeCommunityDoc(ConstitutionAction):
    community_doc = models.ForeignKey(CommunityDoc, models.CASCADE)
    change_text = models.TextField()

    action_codename = 'policykitchangecommunitydoc'

    def execute(self):
        self.community_doc.change_text(self.change_text)

    class Meta:
        permissions = (
            ('can_execute_policykitchangecommunitydoc', 'Can execute policykit change community doc'),
        )


class PolicykitAddRole(ConstitutionAction):
    name = models.CharField('name', max_length=300)
    permissions = models.ManyToManyField(Permission)

    action_codename = 'policykitaddrole'

    def __str__(self):
        perms = ""
        return "Add Role -  name: " + self.name + ", permissions: "

    def execute(self):
        g, _ = CommunityRole.objects.get_or_create(name=self.name)
        for p in self.permissions.all():
            g.permissions.add(p)
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitaddrole', 'Can execute policykit add role'),
        )


class PolicykitDeleteRole(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.SET_NULL, null=True)

    action_codename = 'policykitdeleterole'

    def execute(self):
        self.role.delete()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitdeleterole', 'Can execute policykit delete role'),
        )


class PolicykitAddPermission(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.CASCADE)
    permissions = models.ManyToManyField(Permission)

    action_codename = 'policykitaddpermission'

    def execute(self):
        for p in self.permissions.all():
            self.role.permissions.add(p)
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitaddpermission', 'Can execute policykit add permission'),
        )


class PolicykitRemovePermission(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.CASCADE)
    permissions = models.ManyToManyField(Permission)

    action_codename = 'policykitremovepermission'

    def execute(self):
        for p in self.permissions.all():
            self.role.permissions.remove(p)
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitremovepermission', 'Can execute policykit remove permission'),
        )


class PolicykitAddUserRole(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.CASCADE)
    users = models.ManyToManyField(CommunityUser)

    action_codename = 'policykitadduserrole'

    def execute(self):
        for u in self.users.all():
            self.role.user_set.add(u)
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitadduserrole', 'Can execute policykit add user role'),
        )


class PolicykitRemoveUserRole(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.CASCADE)
    users = models.ManyToManyField(CommunityUser)

    action_codename = 'policykitremoveuserrole'

    def execute(self):
        for u in self.users.all():
            self.role.user_set.remove(u)
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitremoveuserrole', 'Can execute policykit remove user role'),
        )

class EditorModel(ConstitutionAction):
    name = models.TextField(null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    filter = models.TextField(blank=True,
        default=DEFAULT_FILTER,
        verbose_name="Filter"
    )
    initialize = models.TextField(blank=True,
        default=DEFAULT_INITIALIZE,
        verbose_name="Initialize"
    )
    check = models.TextField(blank=True,
        default=DEFAULT_CHECK,
        verbose_name="Check"
    )
    notify = models.TextField(blank=True,
        default=DEFAULT_NOTIFY,
        verbose_name="Notify"
    )
    success = models.TextField(blank=True,
        default=DEFAULT_SUCCESS,
        verbose_name="Pass"
    )
    fail = models.TextField(blank=True,
        default=DEFAULT_FAIL,
        verbose_name="Fail"
    )

class PolicykitAddCommunityPolicy(EditorModel):
    action_codename = 'policykitaddcommunitypolicy'

    def execute(self):
        policy = CommunityPolicy()
        policy.name = self.name
        policy.description = self.description
        policy.is_bundled = self.is_bundled
        policy.filter = self.filter
        policy.initialize = self.initialize
        policy.check = self.check
        policy.notify = self.notify
        policy.success = self.success
        policy.fail = self.fail
        policy.community = self.community
        policy.save()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitaddcommunitypolicy', 'Can execute policykit add community policy'),
        )


class PolicykitAddConstitutionPolicy(EditorModel):
    action_codename = 'policykitaddconstitutionpolicy'

    def execute(self):
        policy = ConstitutionPolicy()
        policy.community = self.community
        policy.description = self.description
        policy.is_bundled = self.is_bundled
        policy.filter = self.filter
        policy.initialize = self.initialize
        policy.check = self.check
        policy.notify = self.notify
        policy.success = self.success
        policy.fail = self.fail
        policy.save()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitaddconstitutionpolicy', 'Can execute policykit add constitution policy'),
        )


class PolicykitChangeCommunityPolicy(EditorModel):
    community_policy = models.ForeignKey('CommunityPolicy', models.CASCADE)

    action_codename = 'policykitchangecommunitypolicy'

    def execute(self):
        self.community_policy.name = self.name
        self.community_policy.description = self.description
        self.community_policy.filter = self.filter
        self.community_policy.initialize = self.initialize
        self.community_policy.check = self.check
        self.community_policy.notify = self.notify
        self.community_policy.success = self.success
        self.community_policy.fail = self.fail
        self.community_policy.save()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitchangecommunitypolicy', 'Can execute policykit change community policy'),
        )


class PolicykitChangeConstitutionPolicy(EditorModel):
    constitution_policy = models.ForeignKey('ConstitutionPolicy', models.CASCADE)

    action_codename = 'policykitchangeconstitutionpolicy'

    def execute(self):
        self.constitution_policy.name = self.name
        self.constitution_policy.description = self.description
        self.constitution_policy.filter = self.filter
        self.constitution_policy.initialize = self.initialize
        self.constitution_policy.check = self.check
        self.constitution_policy.notify = self.notify
        self.constitution_policy.success = self.success
        self.constitution_policy.fail = self.fail
        self.constitution_policy.save()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitchangeconstitutionpolicy', 'Can execute policykit change constitution policy'),
        )


class PolicykitRemoveCommunityPolicy(ConstitutionAction):
    community_policy = models.ForeignKey('CommunityPolicy',
                                         models.SET_NULL,
                                         null=True)

    action_codename = 'policykitremovecommunitypolicy'

    def execute(self):
        self.community_policy.delete()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitremovecommunitypolicy', 'Can execute policykit remove community policy'),
        )


class PolicykitRemoveConstitutionPolicy(ConstitutionAction):
    constitution_policy = models.ForeignKey('ConstitutionPolicy',
                                         models.SET_NULL,
                                         null=True)

    action_codename = 'policykitremoveconstitutionpolicy'

    def execute(self):

        self.constitution_policy.delete()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitremoveconstitutionpolicy', 'Can execute policykit remove constitution policy'),
        )


class CommunityAction(BaseAction,PolymorphicModel):
    ACTION = None
    AUTH = 'app'

    community = models.ForeignKey(Community, models.CASCADE)
    initiator = models.ForeignKey(CommunityUser, models.CASCADE)
    community_revert = models.BooleanField(default=False)
    community_origin = models.BooleanField(default=False)
    is_bundled = models.BooleanField(default=False)

    action_type = "CommunityAction"
    action_codename = ''

    class Meta:
        verbose_name = 'communityaction'
        verbose_name_plural = 'communityactions'

    def revert(self, values, call):
        _ = LogAPICall.make_api_call(self.community, values, call)
        self.community_revert = True
        self.save()

    def execute(self):
        self.community.execute_community_action(self)
        self.pass_action()

    def pass_action(self):
        proposal = self.proposal
        proposal.status = Proposal.PASSED
        proposal.save()

    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            """app_name = ''
            if isinstance(self.community, SlackCommunity):
                app_name = 'slackintegration'
            elif isinstance(self.community, RedditCommunity):
                app_name = 'redditintegration'
            elif isinstance(self.community, DiscordCommunity):
                app_name = 'discordintegration'"""
            #runs only if they have propose permission

            p = Proposal.objects.create(status=Proposal.PROPOSED,
                                            author=self.initiator)
            self.proposal = p
            super(CommunityAction, self).save(*args, **kwargs)

            if not self.is_bundled:
                action = self
                #if they have execute permission, skip all policies
                """if action.initiator.has_perm(app_name + '.can_execute_' + action.action_codename):
                    action.execute()
                else:"""
                    for policy in CommunityPolicy.objects.filter(community=self.community):
                        if filter_policy(policy, action):

                          initialize_policy(policy, action)

                          check_result = check_policy(policy, action)
                          if check_result == Proposal.PASSED:
                              pass_policy(policy, action)
                          elif check_result == Proposal.FAILED:
                              fail_policy(policy, action)
                          else:
                              notify_policy(policy, action)

        else:
            super(CommunityAction, self).save(*args, **kwargs)


class CommunityActionBundle(BaseAction):
    ELECTION = 'election'
    BUNDLE = 'bundle'
    BUNDLE_TYPE = [
        (ELECTION, 'election'),
        (BUNDLE, 'bundle')
    ]

    action_type = "CommunityActionBundle"
    bundled_actions = models.ManyToManyField(CommunityAction)
    bundle_type = models.CharField(choices=BUNDLE_TYPE, max_length=10)

    def execute(self):
        if self.bundle_type == CommunityActionBundle.BUNDLE:
            for action in self.bundled_actions.all():
                self.community.execute_community_action(action)
                action.pass_action()

    def pass_action(self):
        proposal = self.proposal
        proposal.status = Proposal.PASSED
        proposal.save()

    class Meta:
        verbose_name = 'communityactionbundle'
        verbose_name_plural = 'communityactionbundles'


@receiver(post_save, sender=CommunityActionBundle)
@on_transaction_commit
def after_bundle_save(sender, instance, **kwargs):
    action = instance

    #if they have execute permission, skip all policies
    if action.initiator.has_perm('policyengine.can_execute_' + action.action_codename):
        action.execute()
    else:
        if not action.community_post:
            for policy in CommunityPolicy.objects.filter(community=action.community):
              if filter_policy(policy, action):

                  initialize_policy(policy, action)

                  check_result = check_policy(policy, action)
                  if check_result == Proposal.PASSED:
                      pass_policy(policy, action)
                  elif check_result == Proposal.FAILED:
                      fail_policy(policy, action)
                  else:
                      notify_policy(policy, action)

class BasePolicy(models.Model):
    filter = models.TextField(blank=True, default='')
    initialize = models.TextField(blank=True, default='')
    check = models.TextField(blank=True, default='')
    notify = models.TextField(blank=True, default='')
    success = models.TextField(blank=True, default='')
    fail = models.TextField(blank=True, default='')

    name = models.TextField(null=True, blank=True)
    community = models.ForeignKey(Community,
        models.CASCADE,
        verbose_name='community',
    )
    description = models.TextField(null=True, blank=True)
    is_bundled = models.BooleanField(default=False)
    has_notified = models.BooleanField(default=False)

    data = models.OneToOneField(DataStore,
        models.CASCADE,
        verbose_name='data',
        null=True
    )

    class Meta:
        abstract = True


class ConstitutionPolicy(BasePolicy):
    policy_type = "ConstitutionPolicy"

    class Meta:
        verbose_name = 'constitutionpolicy'
        verbose_name_plural = 'constitutionpolicies'

    def __str__(self):
        return ' '.join(['ConstitutionPolicy: ', self.description, 'for', self.community.community_name])


class ConstitutionPolicyBundle(BaseAction):
    bundled_policies = models.ManyToManyField(ConstitutionPolicy)
    policy_type = "ConstitutionPolicyBundle"

    class Meta:
        verbose_name = 'constitutionpolicybundle'
        verbose_name_plural = 'constitutionpolicybundles'


class CommunityPolicy(BasePolicy):
    policy_type = "CommunityPolicy"

    class Meta:
        verbose_name = 'communitypolicy'
        verbose_name_plural = 'communitypolicies'

    def __str__(self):
        return ' '.join(['CommunityPolicy: ', self.description, 'for', self.community.community_name])


class CommunityPolicyBundle(BaseAction):
    bundled_policies = models.ManyToManyField(CommunityPolicy)
    policy_type = "CommunityPolicyBundle"

    class Meta:
        verbose_name = 'communitypolicybundle'
        verbose_name_plural = 'communitypolicybundles'


class UserVote(models.Model):
    user = models.ForeignKey(CommunityUser, models.CASCADE)
    proposal = models.ForeignKey(Proposal, models.CASCADE)
    vote_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class BooleanVote(UserVote):
    boolean_value = models.BooleanField(null=True) # yes/no, selected/not selected


class NumberVote(UserVote):
    number_value = models.IntegerField(null=True)
