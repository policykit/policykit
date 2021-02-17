from django.db import models, transaction
from django.db.models.signals import post_save
from actstream import action
from django.dispatch import receiver
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from polymorphic.models import PolymorphicModel
from django.core.exceptions import ValidationError
from policyengine.views import check_policy, filter_policy, initialize_policy, pass_policy, fail_policy, notify_policy
from datetime import datetime, timezone
import urllib
import json

import logging


logger = logging.getLogger(__name__)

# Default values for code fields in editor
DEFAULT_FILTER = "return True\n\n"
DEFAULT_INITIALIZE = "pass\n\n"
DEFAULT_CHECK = "return PASSED\n\n"
DEFAULT_NOTIFY = "pass\n\n"
DEFAULT_SUCCESS = "action.execute()\n\n"
DEFAULT_FAIL = "pass\n\n"

def on_transaction_commit(func):
    def inner(*args, **kwargs):
        transaction.on_commit(lambda: func(*args, **kwargs))

    return inner


class StarterKit(PolymorphicModel):
    name = models.TextField(null=True, blank=True, default = '')
    platform = models.TextField(null=True, blank=True, default = '')

    def __str__(self):
        return self.name

class Community(PolymorphicModel):
    community_name = models.CharField('team_name', max_length=1000)
    platform = None
    base_role = models.OneToOneField('CommunityRole', models.CASCADE, related_name='base_community')

    def notify_action(self, action, policy, users):
        pass

    def get_users(self, users):
      return users

class CommunityRole(Group):
    community = models.ForeignKey(Community, models.CASCADE, null=True)
    role_name = models.TextField('readable_name', max_length=300, null=True)
    description = models.TextField(null=True, blank=True, default='')

    class Meta:
        verbose_name = 'communityrole'
        verbose_name_plural = 'communityroles'

    def save(self, *args, **kwargs):
        super(CommunityRole, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.role_name)

class CommunityUser(User, PolymorphicModel):
    readable_name = models.CharField('readable_name', max_length=300, null=True)
    community = models.ForeignKey(Community, models.CASCADE)
    access_token = models.CharField('access_token', max_length=300, null=True)
    is_community_admin = models.BooleanField(default=False)
    avatar = models.CharField('avatar', max_length=500, null=True)

    def __str__(self):
        return self.readable_name if self.readable_name else self.username

    def save(self, *args, **kwargs):
        super(CommunityUser, self).save(*args, **kwargs)
        group = self.community.base_role
        group.user_set.add(self)

    def get_roles(self):
        user_roles = []
        roles = CommunityRole.objects.filter(community=self.community)
        for r in roles:
            if self in r.user_set.all():
                user_roles.append(r.role_name)
        return user_roles

    def has_role(self, role_name):
        roles = CommunityRole.objects.filter(community=self.community, role_name=role_name)
        return roles.count() > 0

class CommunityDoc(models.Model):
    name = models.TextField(null=True, blank=True, default = '')
    text = models.TextField(null=True, blank=True, default = '')
    community = models.ForeignKey(Community, models.CASCADE, null=True)

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        super(CommunityDoc, self).save(*args, **kwargs)

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
    def make_api_call(cls, community, values, call, action=None, method=None):
        _ = LogAPICall.objects.create(community=community,
                                      call_type=call,
                                      extra_info=json.dumps(values)
                                      )
        res = community.make_call(call, values=values, action=action, method=method)
        return res

class GenericPolicy(models.Model):
    starterkit = models.ForeignKey(StarterKit, on_delete=models.CASCADE)
    name = models.TextField(null=True, blank=True, default = '')
    description = models.TextField(null=True, blank=True, default = '')
    filter = models.TextField(null=True, blank=True, default='')
    initialize = models.TextField(null=True, blank=True, default='')
    check = models.TextField(null=True, blank=True, default='')
    notify = models.TextField(null=True, blank=True, default='')
    success = models.TextField(null=True, blank=True, default='')
    fail = models.TextField(null=True, blank=True, default='')
    is_bundled = models.BooleanField(default=False)
    has_notified = models.BooleanField(default=False)
    is_constitution = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class GenericRole(Group):
    starterkit = models.ForeignKey(StarterKit, on_delete=models.CASCADE)
    role_name = models.TextField(blank=True, null=True, default='')
    description = models.TextField(blank=True, null=True, default='')
    is_base_role = models.BooleanField(default=False)
    user_group = models.TextField(blank=True, null=True, default='')
    plat_perm_set = models.TextField(blank=True, null=True, default='')

    def __str__(self):
        return self.role_name

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

    def get_boolean_votes(self, value, users=None):
        if users:
            votes = BooleanVote.objects.filter(boolean_value=value, proposal=self, user__in=users)
        else:
            votes = BooleanVote.objects.filter(boolean_value=value, proposal=self)
        return votes

    def get_yes_votes(self, users=None):
        return self.get_boolean_votes(True, users)

    def get_no_votes(self, users=None):
        return self.get_boolean_votes(False, users)

    def get_num_yes_votes(self, users=None):
        return self.get_yes_votes(users).count()

    def get_num_no_votes(self, users=None):
        return self.get_no_votes(users).count()

    def get_number_votes(self, value=0, users=None):
        if users:
            votes = NumberVote.objects.filter(number_value=value, proposal=self, user__in=users)
        else:
            votes = NumberVote.objects.filter(number_value=value, proposal=self)
        return votes

    def get_total_vote_count(self, vote_type, vote_number = 1, users = None):
        vote_type = vote_type.lower()

        totalDict = {}
        if vote_type == "boolean":
            totaldict["True"] = len(get_yes_votes(users))
            totaldict["False"] = len(get_no_votes(users))
        elif vote_type == "number":
            for vote_num in range(1, vote_number):
                totalDict[vote_num] = get_number_votes(vote_num)

        return totalDict

    def get_raw_number_votes(self, value = 0, users = None):
        votingDict = {}
        if users:
            for i in users:
                votingDict[i] = [NumberVote.objects.filter(number_value=value, proposal=self, user__in=users)]
        else:
            for i in users:
                votingDict[i] = [NumberVote.objects.filter(number_value=value, proposal=self)]
        return users

    def get_raw_boolean_votes(self, value, users = None):
        votingDict = {}
        if users:
            for i in users:
                votingDict[i] = [BooleanVote.objects.filter(boolean_value= value, proposal=self, user__in=users)]
        else:
            for i in users:
                votingDict[i] = [BooleanVote.objects.filter(boolean_value_value=value, proposal=self)]
        return users

    def time_elapsed(self):
        logger.info('time elapsed')
        logger.info(datetime.now(timezone.utc))
        logger.info(self.proposal_time)
        return datetime.now(timezone.utc) - self.proposal_time

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

    app_name = 'policyengine'

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
        action.send(self, verb='was passed')

    def shouldCreate(self):
        return not self.pk # Runs only when object is new

    def save(self, *args, **kwargs):
        logger.info('Constitution Action: running save')
        if self.shouldCreate():
            if self.data is None:
                ds = DataStore.objects.create()
                self.data = ds

            #runs only if they have propose permission
            if self.initiator.has_perm(self._meta.app_label + '.add_' + self.action_codename):
                logger.info('Constitution Action: has perm')
                if hasattr(self, 'proposal'):
                    self.proposal.status = Proposal.PROPOSED
                else:
                    self.proposal = Proposal.objects.create(status=Proposal.PROPOSED, author=self.initiator)
                super(ConstitutionAction, self).save(*args, **kwargs)

                if not self.is_bundled:
                    action = self
                    #if they have execute permission, skip all policies
                    if action.initiator.has_perm(action.app_name + '.can_execute_' + action.action_codename):
                        logger.info('Constitution Action: has execute permissions')
                        action.execute()
                    else:
                        logger.info('Constitution Action: about to filter')
                        for policy in ConstitutionPolicy.objects.filter(community=self.community):
                          if filter_policy(policy, action):
                              logger.info('Constitution Action: just filtered')

                              initialize_policy(policy, action)
                              logger.info(action.proposal.status)

                              logger.info('Constitution Action: about to check')
                              check_result = check_policy(policy, action)
                              logger.info('Constitution Action: just checked')
                              if check_result == Proposal.PASSED:
                                  logger.info('Constitution Action: passed')
                                  pass_policy(policy, action)
                              elif check_result == Proposal.FAILED:
                                  logger.info('Constitution Action: failed')
                                  fail_policy(policy, action)
                              else:
                                  logger.info('Constitution Action: notifying')
                                  notify_policy(policy, action)
                                  logger.info(action.proposal.status)
            else:
                logger.info('failed one')
                self.proposal = Proposal.objects.create(status=Proposal.FAILED, author=self.initiator)
        else:
            if not self.pk: # Runs only when object is new
                logger.info('failed two')
                self.proposal = Proposal.objects.create(status=Proposal.FAILED, author=self.initiator)
            logger.info('else save')
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
    if action.initiator.has_perm(action.app_name + '.add_' + action.action_codename):
        #if they have execute permission, skip all policies
        if action.initiator.has_perm(action.app_name + '.can_execute_' + action.action_codename):
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

class PolicykitAddCommunityDoc(ConstitutionAction):
    name = models.TextField()
    text = models.TextField()

    action_codename = 'policykitaddcommunitydoc'

    def __str__(self):
        return "Add Document: " + self.name

    def execute(self):
        doc, _ = CommunityDoc.objects.get_or_create(name=self.name, text=self.text)
        doc.community = self.community
        doc.save()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitaddcommunitydoc', 'Can execute policykit add community doc'),
        )

class PolicykitChangeCommunityDoc(ConstitutionAction):
    doc = models.ForeignKey(CommunityDoc, models.SET_NULL, null=True)
    name = models.TextField()
    text = models.TextField()

    action_codename = 'policykitchangecommunitydoc'

    def __str__(self):
        return "Edit Document: " + self.name

    def execute(self):
        self.doc.name = self.name
        self.doc.text = self.text
        self.doc.save()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitchangecommunitydoc', 'Can execute policykit change community doc'),
        )

class PolicykitDeleteCommunityDoc(ConstitutionAction):
    doc = models.ForeignKey(CommunityDoc, models.SET_NULL, null=True)

    action_codename = 'policykitdeletecommunitydoc'

    def __str__(self):
        if self.doc:
            return "Delete Document: " + self.doc.name
        return "Delete Document"

    def execute(self):
        self.doc.delete()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitdeletecommunitydoc', 'Can execute policykit delete community doc'),
        )

class PolicykitAddRole(ConstitutionAction):
    name = models.CharField('name', max_length=300)
    description = models.TextField(null=True, blank=True, default='')
    permissions = models.ManyToManyField(Permission)

    action_codename = 'policykitaddrole'
    ready = False

    def __str__(self):
        return "Add Role: " + self.name

    def shouldCreate(self):
        return self.ready

    def execute(self):
        role, _ = CommunityRole.objects.get_or_create(
            role_name=self.name,
            name=self.community.platform + ": " + self.community.community_name + ": " + self.name,
            description=self.description
        )
        for p in self.permissions.all():
            role.permissions.add(p)
        role.community = self.community
        role.save()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitaddrole', 'Can execute policykit add role'),
        )

class PolicykitDeleteRole(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.SET_NULL, null=True)

    action_codename = 'policykitdeleterole'

    def __str__(self):
        if self.role:
            return "Delete Role: " + self.role.role_name
        else:
            return "Delete Role: [ERROR: role not found]"

    def execute(self):
        try:
            self.role.delete()
        except AssertionError: # Triggers if object has already been deleted
            pass
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitdeleterole', 'Can execute policykit delete role'),
        )

class PolicykitEditRole(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.SET_NULL, null=True)
    name = models.CharField('name', max_length=300)
    description = models.TextField(null=True, blank=True, default='')
    permissions = models.ManyToManyField(Permission)

    action_codename = 'policykiteditrole'
    ready = False

    def __str__(self):
        return "Edit Role: " + self.name

    def shouldCreate(self):
        return self.ready

    def execute(self):
        self.role.role_name = self.name
        self.role.description = self.description
        self.role.permissions.clear()
        for p in self.permissions.all():
            self.role.permissions.add(p)
        self.role.save()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykiteditrole', 'Can execute policykit edit role'),
        )

class PolicykitAddUserRole(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.CASCADE)
    users = models.ManyToManyField(CommunityUser)

    action_codename = 'policykitadduserrole'
    ready = False

    def __str__(self):
        if self.role:
            return "Add User: " + str(self.users.all()[0]) + " to Role: " + self.role.role_name
        else:
            return "Add User to Role: [ERROR: role not found]"

    def shouldCreate(self):
        return self.ready

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
    ready = False

    def __str__(self):
        if self.role:
            return "Remove User: " + str(self.users.all()[0]) + " from Role: " + self.role.role_name
        else:
            return "Remove User from Role: [ERROR: role not found]"

    def shouldCreate(self):
        return self.ready

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

class PolicykitAddPlatformPolicy(EditorModel):
    action_codename = 'policykitaddplatformpolicy'

    def __str__(self):
        return "Add Platform Policy: " + self.name

    def execute(self):
        policy = PlatformPolicy()
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
            ('can_execute_addpolicykitplatformpolicy', 'Can execute policykit add platform policy'),
        )

class PolicykitAddConstitutionPolicy(EditorModel):
    action_codename = 'policykitaddconstitutionpolicy'

    def __str__(self):
        return "Add Constitution Policy: " + self.name

    def execute(self):
        policy = ConstitutionPolicy()
        policy.community = self.community
        policy.name = self.name
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

class PolicykitChangePlatformPolicy(EditorModel):
    platform_policy = models.ForeignKey('PlatformPolicy', models.CASCADE)

    action_codename = 'policykitchangeplatformpolicy'

    def __str__(self):
        return "Edit Platform Policy: " + self.name

    def execute(self):
        self.platform_policy.name = self.name
        self.platform_policy.description = self.description
        self.platform_policy.filter = self.filter
        self.platform_policy.initialize = self.initialize
        self.platform_policy.check = self.check
        self.platform_policy.notify = self.notify
        self.platform_policy.success = self.success
        self.platform_policy.fail = self.fail
        self.platform_policy.save()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitchangeplatformpolicy', 'Can execute policykit change platform policy'),
        )

class PolicykitChangeConstitutionPolicy(EditorModel):
    constitution_policy = models.ForeignKey('ConstitutionPolicy', models.CASCADE)

    action_codename = 'policykitchangeconstitutionpolicy'

    def __str__(self):
        return "Edit Constitution Policy: " + self.name

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

class PolicykitRemovePlatformPolicy(ConstitutionAction):
    platform_policy = models.ForeignKey('PlatformPolicy',
                                         models.SET_NULL,
                                         null=True)

    action_codename = 'policykitremoveplatformpolicy'

    def __str__(self):
        if self.platform_policy:
            return "Remove Platform Policy: " + self.platform_policy.name
        else:
            return "Remove Platform Policy: [ERROR: platform policy not found]"

    def execute(self):
        self.platform_policy.delete()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitremoveplatformpolicy', 'Can execute policykit remove platform policy'),
        )

class PolicykitRemoveConstitutionPolicy(ConstitutionAction):
    constitution_policy = models.ForeignKey('ConstitutionPolicy',
                                         models.SET_NULL,
                                         null=True)

    action_codename = 'policykitremoveconstitutionpolicy'

    def __str__(self):
        if self.constitution_policy:
            return "Remove Constitution Policy: " + self.constitution_policy.name
        else:
            return "Remove Constitution Policy: [ERROR: constitution policy not found]"

    def execute(self):
        self.constitution_policy.delete()
        self.pass_action()

    class Meta:
        permissions = (
            ('can_execute_policykitremoveconstitutionpolicy', 'Can execute policykit remove constitution policy'),
        )

class PlatformAction(BaseAction,PolymorphicModel):
    ACTION = None
    AUTH = 'app'

    community = models.ForeignKey(Community, models.CASCADE)
    initiator = models.ForeignKey(CommunityUser, models.CASCADE)
    community_revert = models.BooleanField(default=False)
    community_origin = models.BooleanField(default=False)
    is_bundled = models.BooleanField(default=False)

    action_type = "PlatformAction"
    action_codename = ''

    class Meta:
        verbose_name = 'platformaction'
        verbose_name_plural = 'platformactions'

    def revert(self, values, call, method=None):
        _ = LogAPICall.make_api_call(self.community, values, call, method=method)
        self.community_revert = True
        self.save()

    def execute(self):
        self.community.execute_platform_action(self)
        self.pass_action()

    def pass_action(self):
        proposal = self.proposal
        proposal.status = Proposal.PASSED
        proposal.save()
        action.send(self, verb='was passed')

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.data is None:
                ds = DataStore.objects.create()
                self.data = ds

            #runs only if they have propose permission
            if self.initiator.has_perm(self._meta.app_label + '.add_' + self.action_codename):
                p = Proposal.objects.create(status=Proposal.PROPOSED,
                                                author=self.initiator)
                self.proposal = p

                super(PlatformAction, self).save(*args, **kwargs)

                if not self.is_bundled:
                    action = self
                    #if they have execute permission, skip all policies
                    if action.initiator.has_perm(action.app_name + '.can_execute_' + action.action_codename):
                        action.execute()
                    else:
                        for policy in PlatformPolicy.objects.filter(community=self.community):
                            if filter_policy(policy, action):

                                logger.info('passed filter: ' + policy.name)

                                initialize_policy(policy, action)

                                logger.info('about to check policy: ' + policy.name)

                                check_result = check_policy(policy, action)

                                logger.info('just checked policy: ' + policy.name)
                                if check_result == Proposal.PASSED:
                                    pass_policy(policy, action)
                                elif check_result == Proposal.FAILED:
                                    fail_policy(policy, action)
                                    if self.community_origin:
                                        self.community_revert = True
                                else:
                                    if self.community_origin:
                                        self.community_revert = True
                                    notify_policy(policy, action)
                            else:
                                logger.info('failed filter: ' + policy.name)
            else:
                p = Proposal.objects.create(status=Proposal.FAILED,
                                            author=self.initiator)
                self.proposal = p
        else:
            super(PlatformAction, self).save(*args, **kwargs)

class PlatformActionBundle(BaseAction):
    ELECTION = 'election'
    BUNDLE = 'bundle'
    BUNDLE_TYPE = [
        (ELECTION, 'election'),
        (BUNDLE, 'bundle')
    ]

    action_type = "PlatformActionBundle"
    bundled_actions = models.ManyToManyField(PlatformAction)
    bundle_type = models.CharField(choices=BUNDLE_TYPE, max_length=10)

    def execute(self):
        if self.bundle_type == PlatformActionBundle.BUNDLE:
            for action in self.bundled_actions.all():
                self.community.execute_platform_action(action)
                action.pass_action()

    def pass_action(self):
        proposal = self.proposal
        proposal.status = Proposal.PASSED
        proposal.save()

    class Meta:
        verbose_name = 'platformactionbundle'
        verbose_name_plural = 'platformactionbundles'

@receiver(post_save, sender=PlatformActionBundle)
@on_transaction_commit
def after_bundle_save(sender, instance, **kwargs):
    action = instance

    if action.initiator.has_perm(action.app_name + '.add_' + action.action_codename):
        #if they have execute permission, skip all policies
        if action.initiator.has_perm(action.app_name + '.can_execute_' + action.action_codename):
            action.execute()
        else:
            if not action.community_post:
                for policy in PlatformPolicy.objects.filter(community=action.community):
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

class ConstitutionPolicyBundle(BasePolicy):
    bundled_policies = models.ManyToManyField(ConstitutionPolicy)
    policy_type = "ConstitutionPolicyBundle"

    class Meta:
        verbose_name = 'constitutionpolicybundle'
        verbose_name_plural = 'constitutionpolicybundles'

class PlatformPolicy(BasePolicy):
    policy_type = "PlatformPolicy"

    class Meta:
        verbose_name = 'platformpolicy'
        verbose_name_plural = 'platformpolicies'

    def __str__(self):
        return ' '.join(['PlatformPolicy: ', self.description, 'for', self.community.community_name])

class PlatformPolicyBundle(BasePolicy):
    bundled_policies = models.ManyToManyField(PlatformPolicy)
    policy_type = "PlatformPolicyBundle"

    class Meta:
        verbose_name = 'platformpolicybundle'
        verbose_name_plural = 'platformpolicybundles'

class ExternalProcess(models.Model):
    json_data = models.CharField(max_length=500, blank=True, null=True)
    policy = models.ForeignKey(PlatformPolicy, on_delete=models.CASCADE)
    action = models.ForeignKey(PlatformAction, on_delete=models.CASCADE)

    class Meta:
        unique_together = ['policy', 'action']

class UserVote(models.Model):
    user = models.ForeignKey(CommunityUser, models.CASCADE)
    proposal = models.ForeignKey(Proposal, models.CASCADE)
    vote_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

class BooleanVote(UserVote):
    TRUE_FALSE_CHOICES = (
                          (True, 'Yes'),
                          (False, 'No')
                          )
    boolean_value = models.BooleanField(null = True, choices = TRUE_FALSE_CHOICES,
                                                               default= True) # yes/no, selected/not selected

class NumberVote(UserVote):
    number_value = models.IntegerField(null=True)
