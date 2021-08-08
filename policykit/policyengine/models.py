from django.db import models, transaction
from actstream import action as actstream_action
import requests
from django.contrib.auth.models import UserManager, User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.forms import ModelForm
from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from polymorphic.models import PolymorphicModel, PolymorphicManager
import integrations.metagov.api as MetagovAPI
from policyengine.utils import ActionKind
from policyengine import engine
from datetime import datetime, timezone
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
    """Starter Kit"""

    name = models.TextField(null=True, blank=True, default = '')
    """The name of the starter kit."""

    platform = models.TextField(null=True, blank=True, default = '')
    """The name of the platform ('Slack', 'Reddit', etc.)."""

    def __str__(self):
        return self.name


class Community(models.Model):
    readable_name = models.CharField(max_length=300, blank=True)
    metagov_slug = models.SlugField(max_length=36, unique=True, null=True, blank=True)

    def __str__(self):
        prefix = super().__str__()
        return '{} {}'.format(prefix, self.readable_name or '')

    def save(self, *args, **kwargs):
        if settings.METAGOV_ENABLED and not self.pk and not self.metagov_slug:
            # If this is the first save, create a corresponding community in Metagov
            response = MetagovAPI.create_empty_metagov_community(self.readable_name)
            self.metagov_slug = response["slug"]
            logger.debug(f"Created new Metagov community '{self.metagov_slug}' Saving slug in model.")
        super(Community, self).save(*args, **kwargs)


@receiver(post_delete, sender=Community)
def post_delete_community(sender, instance, **kwargs):
    if instance.metagov_slug and settings.METAGOV_ENABLED:
        MetagovAPI.delete_community(instance.metagov_slug)


class CommunityPlatform(PolymorphicModel):
    """Community on a specific platform"""

    community_name = models.CharField('team_name', max_length=1000)
    """The name of the community."""

    platform = None
    """The name of the platform ('Slack', 'Reddit', etc.)."""

    base_role = models.OneToOneField('CommunityRole', models.CASCADE, related_name='base_community')
    """The default role which users have."""

    community = models.ForeignKey(Community, models.CASCADE)

    def __str__(self):
        return self.community_name

    @property
    def metagov_slug(self):
        return self.community.metagov_slug

    def initiate_vote(self, action, policy, users):
        """
        Sends a notification to users of a pending action.

        Parameters
        -------
        action
            The pending action.
        policy
            The policy being proposed.
        users
            The users who should be notified.
        """
        pass

    def get_roles(self):
        """
        Returns a QuerySet of all roles in the community.
        """
        return CommunityRole.objects.filter(community=self)

    def get_platform_policies(self):
        """
        Returns a QuerySet of all platform policies in the community.
        """
        return Policy.platform_policies.filter(community=self).order_by('-modified_at')

    def get_constitution_policies(self):
        """
        Returns a QuerySet of all constitution policies in the community.
        """
        return Policy.constitution_policies.filter(community=self).order_by('-modified_at')

    def get_documents(self):
        """
        Returns a QuerySet of all documents in the community.
        """
        return CommunityDoc.objects.filter(community=self)

    def save(self, *args, **kwargs):
        """
        Saves the community. Note: Only meant for internal use.
        """
        super(CommunityPlatform, self).save(*args, **kwargs)

class CommunityRole(Group):
    """CommunityRole"""

    community = models.ForeignKey(CommunityPlatform, models.CASCADE, null=True)
    """The community which the role belongs to."""

    role_name = models.TextField('readable_name', max_length=300, null=True)
    """The readable name of the role."""

    description = models.TextField(null=True, blank=True, default='')
    """The readable description of the role. May be empty."""

    class Meta:
        verbose_name = 'communityrole'
        verbose_name_plural = 'communityroles'

    def save(self, *args, **kwargs):
        """
        Saves the role. Note: Only meant for internal use.
        """
        super(CommunityRole, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.role_name)

class PolymorphicUserManager(UserManager, PolymorphicManager):
    # no-op class to get rid of warnings (issue #270)
    pass

# https://github.com/django-polymorphic/django-polymorphic/issues/9
setattr(User, '_base_objects', User.objects)

class CommunityUser(User, PolymorphicModel):
    """CommunityUser"""

    readable_name = models.CharField('readable_name', max_length=300, null=True)
    """The readable name of the user. May or may not exist."""

    community = models.ForeignKey(CommunityPlatform, models.CASCADE)
    """The community which the user belongs to."""

    access_token = models.CharField('access_token', max_length=300, null=True)
    """The access token which the user uses on login. May or may not exist."""

    is_community_admin = models.BooleanField(default=False)
    """True if the user is an admin. Default is False."""

    avatar = models.CharField('avatar', max_length=500, null=True)
    """The URL of the avatar image of the user. May or may not exist."""

    objects = PolymorphicUserManager()

    def __str__(self):
        return self.readable_name if self.readable_name else self.username

    def get_roles(self):
        """
        Returns a list containing all of the user's roles.
        """
        user_roles = []
        roles = CommunityRole.objects.filter(community=self.community)
        for r in roles:
            for u in r.user_set.all():
                if u.communityuser.username == self.username:
                    user_roles.append(r)
        return user_roles

    def has_role(self, role_name):
        """
        Returns True if the user has a role with the specified role_name.

        Parameters
        -------
        role_name
            The name of the role to check for.
        """
        roles = CommunityRole.objects.filter(community=self.community, role_name=role_name)
        if roles.exists():
            r = roles[0]
            for u in r.user_set.all():
                if u.communityuser.username == self.username:
                    return True
        return False

    def save(self, *args, **kwargs):
        """
        Saves the user. Note: Only meant for internal use.
        """
        super(CommunityUser, self).save(*args, **kwargs)
        self.community.base_role.user_set.add(self)

        # If this user is an admin in the community, give them access to edit the Metagov config
        if self.is_community_admin and settings.METAGOV_ENABLED:
            from integrations.metagov.models import MetagovConfig
            role_name = "Metagov Admin"
            group_name = f"{self.community.platform}: {self.community.community_name}: {role_name}"
            role,created = CommunityRole.objects.get_or_create(community=self.community, role_name=role_name, name=group_name)
            if created:
                content_type = ContentType.objects.get_for_model(MetagovConfig)
                role.permissions.set(Permission.objects.filter(content_type=content_type))

            role.user_set.add(self)

class CommunityDoc(models.Model):
    """CommunityDoc"""

    name = models.TextField(null=True, blank=True, default = '')
    """The name of the document."""

    text = models.TextField(null=True, blank=True, default = '')
    """The text within the document."""

    community = models.ForeignKey(CommunityPlatform, models.CASCADE, null=True)
    """The community which the document belongs to."""

    is_active = models.BooleanField(default=True)
    """True if the document is active. Default is True."""

    def __str__(self):
        return str(self.name)

    def save(self, *args, **kwargs):
        """
        Saves the document. Note: Only meant for internal use.
        """
        super(CommunityDoc, self).save(*args, **kwargs)

class DataStore(models.Model):
    """DataStore"""

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
        """
        Returns the value associated with the given key.

        Parameters
        -------
        key
            The key associated with the value.
        """
        obj = self._get_data_store()
        return obj.get(key, None)

    def set(self, key, value):
        """
        Stores the given value, referenced by the given key.

        Parameters
        -------
        key
            The key to associate with the given value.
        value
            The value to store.
        """
        obj = self._get_data_store()
        obj[key] = value
        self._set_data_store(obj)
        return True # NOTE: Why does this line exist?

    def remove(self, key):
        """
        Removes the value associated with the given key. Returns True if a value was found and removed. Returns False otherwise.

        Parameters
        -------
        key
            The key associated with the value to be removed.
        """
        obj = self._get_data_store()
        res = obj.pop(key, None)
        self._set_data_store(obj)
        if not res:
            return False
        return True


class LogAPICall(models.Model):
    community = models.ForeignKey(CommunityPlatform, models.CASCADE)
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
    is_constitution = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

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

class PolicyEvaluation(models.Model):
    """PolicyEvaluation"""

    PROPOSED = 'proposed'
    FAILED = 'failed'
    PASSED = 'passed'
    STATUS = [
        (PROPOSED, 'proposed'),
        (FAILED, 'failed'),
        (PASSED, 'passed')
    ]

    proposal_time = models.DateTimeField(auto_now_add=True)
    """Datetime object representing when the first evaluation started."""

    status = models.CharField(choices=STATUS, max_length=10)
    """Status of the evaluation. One of PROPOSED, PASSED or FAILED."""

    policy = models.ForeignKey('Policy', on_delete=models.SET_NULL, editable=False, blank=True, null=True)
    """The policy that is being evaluated."""

    action = models.ForeignKey('BaseAction', on_delete=models.CASCADE, editable=False)
    """The action that triggered the evaluation."""

    governance_process_url = models.URLField(max_length=100, blank=True)
    """URL for the GovernanceProcess that is being used to make a decision about this PolicyEvaluation"""

    governance_process_json = models.JSONField(max_length=1000, null=True, blank=True)
    """Serialized Metagov governance process"""

    data = models.OneToOneField(DataStore, models.CASCADE, null=True, blank=True)
    """The datastore containing any additional data to persist for the evaluation."""

    def __str__(self):
        return f"PolicyEvaluation {self.pk}: {self.action} : {self.policy or 'POLICY_DELETED'} ({self.status})"

    def get_time_elapsed(self):
        """
        Returns a datetime object representing the time elapsed since the first evaluation.
        """
        return datetime.now(timezone.utc) - self.proposal_time

    def get_all_boolean_votes(self, users=None):
        """
        For Boolean voting. Returns all boolean votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.
        """
        if users:
            return BooleanVote.objects.filter(evaluation=self, user__in=users)
        return BooleanVote.objects.filter(evaluation=self)

    def get_yes_votes(self, users=None):
        """
        For Boolean voting. Returns the yes votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.
        """
        if users:
            return BooleanVote.objects.filter(boolean_value=True, evaluation=self, user__in=users)
        return BooleanVote.objects.filter(boolean_value=True, evaluation=self)

    def get_no_votes(self, users=None):
        """
        For Boolean voting. Returns the no votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.
        """
        if users:
            return BooleanVote.objects.filter(boolean_value=False, evaluation=self, user__in=users)
        return BooleanVote.objects.filter(boolean_value=False, evaluation=self)

    def get_all_number_votes(self, users=None):
        """
        For Number voting. Returns all number votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.
        """
        if users:
            return NumberVote.objects.filter(evaluation=self, user__in=users)
        return NumberVote.objects.filter(evaluation=self)

    def get_one_number_votes(self, value, users=None):
        """
        For Number voting. Returns number votes for the specified value as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.
        """
        if users:
            return NumberVote.objects.filter(number_value=value, evaluation=self, user__in=users)
        return NumberVote.objects.filter(number_value=value, evaluation=self)

    def save(self, *args, **kwargs):
        """
        Saves the evaluation. Note: Only meant for internal use.
        """
        if not self.pk:
            self.data = DataStore.objects.create()
        super(PolicyEvaluation, self).save(*args, **kwargs)

    def pass_action(self):
        """
        Sets the evaluation to PASSED.
        """
        self.status = PolicyEvaluation.PASSED
        self.save()
        action = self.action
        actstream_action.send(action, verb='was passed', community_id=action.community.id, action_codename=action.action_type_new)

    def fail_action(self):
        """
        Sets the evaluation to FAILED.
        """
        self.status = PolicyEvaluation.FAILED
        self.save()
        action = self.action
        actstream_action.send(action, verb='was failed', community_id=action.community.id, action_codename=action.action_type_new)

class BaseAction(PolymorphicModel):
    """Base Action"""

    community = models.ForeignKey(CommunityPlatform, models.CASCADE, verbose_name='community')
    """The community in which the action is taking place."""

    initiator = models.ForeignKey(CommunityUser, models.CASCADE, blank=True, null=True)
    """The User who initiated the action. May not exist if initiated by PolicyKit."""

    # TODO: move to PolicyEvaluation
    community_post = models.CharField('community_post', max_length=300, null=True)
    """The notification which is sent to the community to alert them of the action. May or may not exist."""

    is_bundled = models.BooleanField(default=False)
    """True if the action is part of a bundle."""

    # TODO: DELETE
    action_codename = ''
    """The codename of the action."""

    action_kind = None # platform vs constitution. don't override

    def save(self, *args, **kwargs):
        """
        Saves the action. If new, evaluates against current policies. Note: Only meant for internal use.
        """
        if not self.pk:
            # Runs if initiator has propose permission, OR if there is no initiator.
            can_propose_perm = f"{self._meta.app_label}.add_{self.action_type_new}"
            if not self.initiator or self.initiator.has_perm(can_propose_perm):
                super(BaseAction, self).save(*args, **kwargs)
                engine.govern_action(self)

        super(BaseAction, self).save(*args, **kwargs)

    @property
    def action_type_new(self):
        """accessor so policy authors can access model name using a nicer attribute"""
        return self._meta.model_name

class ConstitutionAction(BaseAction, PolymorphicModel):
    """Constitution Action"""

    action_type = "ConstitutionAction" # DELETE
    action_kind = ActionKind.CONSTITUTION

    class Meta:
        verbose_name = 'constitutionaction'
        verbose_name_plural = 'constitutionactions'

class ConstitutionActionBundle(BaseAction):
    ELECTION = 'election'
    BUNDLE = 'bundle'
    BUNDLE_TYPE = [
        (ELECTION, 'election'),
        (BUNDLE, 'bundle')
    ]

    action_type = "ConstitutionActionBundle" # DELETE
    action_kind = ActionKind.CONSTITUTION

    bundled_actions = models.ManyToManyField(ConstitutionAction)
    bundle_type = models.CharField(choices=BUNDLE_TYPE, max_length=10)

    def execute(self):
        if self.bundle_type == ConstitutionActionBundle.BUNDLE:
            for action in self.bundled_actions.all():
                action.execute()

    class Meta:
        verbose_name = 'constitutionactionbundle'
        verbose_name_plural = 'constitutionactionbundles'

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
        return "Delete Document: [ERROR: doc not found]"

    def execute(self):
        self.doc.is_active = False
        self.doc.save()

    class Meta:
        permissions = (
            ('can_execute_policykitdeletecommunitydoc', 'Can execute policykit delete community doc'),
        )

class PolicykitRecoverCommunityDoc(ConstitutionAction):
    doc = models.ForeignKey(CommunityDoc, models.SET_NULL, null=True)

    action_codename = 'policykitrecovercommunitydoc'

    def __str__(self):
        if self.doc:
            return "Recover Document: " + self.doc.name
        return "Recover Document: [ERROR: doc not found]"

    def execute(self):
        self.doc.is_active = True
        self.doc.save()

    class Meta:
        permissions = (
            ('can_execute_policykitrecovercommunitydoc', 'Can execute policykit recover community doc'),
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
        first_user = self.users.first()
        if self.role and first_user:
            return "Add User: " + str(first_user) + " to Role: " + self.role.role_name
        elif first_user is None:
            return f"Add User: [ERROR: no users] to role {self.role.role_name}"
        else:
            return "Add User to Role: [ERROR: role not found]"

    def shouldCreate(self):
        return self.ready

    def execute(self):
        for u in self.users.all():
            self.role.user_set.add(u)

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

    class Meta:
        permissions = (
            ('can_execute_policykitremoveuserrole', 'Can execute policykit remove user role'),
        )

class EditorModel(ConstitutionAction):
    name = models.CharField(max_length=100)
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

    def save(self, *args, **kwargs):
        if not self.name:
            raise ValidationError("Name is required.")
        super(EditorModel, self).save(*args, **kwargs)

class PolicykitAddPlatformPolicy(EditorModel):
    action_codename = 'policykitaddplatformpolicy'

    def __str__(self):
        return "Add Platform Policy: " + self.name

    def execute(self):
        policy = Policy()
        policy.kind = Policy.PLATFORM
        policy.name = self.name
        policy.description = self.description
        policy.filter = self.filter
        policy.initialize = self.initialize
        policy.check = self.check
        policy.notify = self.notify
        policy.success = self.success
        policy.fail = self.fail
        policy.community = self.community
        policy.save()

    class Meta:
        permissions = (
            ('can_execute_addpolicykitplatformpolicy', 'Can execute policykit add platform policy'),
        )

class PolicykitAddConstitutionPolicy(EditorModel):
    action_codename = 'policykitaddconstitutionpolicy'

    def __str__(self):
        return "Add Constitution Policy: " + self.name

    def execute(self):
        policy = Policy()
        policy.kind = Policy.CONSTITUTION
        policy.community = self.community
        policy.name = self.name
        policy.description = self.description
        policy.filter = self.filter
        policy.initialize = self.initialize
        policy.check = self.check
        policy.notify = self.notify
        policy.success = self.success
        policy.fail = self.fail
        policy.save()

    class Meta:
        permissions = (
            ('can_execute_policykitaddconstitutionpolicy', 'Can execute policykit add constitution policy'),
        )

class PolicykitChangePlatformPolicy(EditorModel):
    platform_policy = models.ForeignKey('Policy', models.CASCADE)

    action_codename = 'policykitchangeplatformpolicy'

    def __str__(self):
        return "Change Platform Policy: " + self.name

    def execute(self):
        assert self.platform_policy.kind == Policy.PLATFORM
        self.platform_policy.name = self.name
        self.platform_policy.description = self.description
        self.platform_policy.filter = self.filter
        self.platform_policy.initialize = self.initialize
        self.platform_policy.check = self.check
        self.platform_policy.notify = self.notify
        self.platform_policy.success = self.success
        self.platform_policy.fail = self.fail
        self.platform_policy.save()

    class Meta:
        permissions = (
            ('can_execute_policykitchangeplatformpolicy', 'Can execute policykit change platform policy'),
        )

class PolicykitChangeConstitutionPolicy(EditorModel):
    constitution_policy = models.ForeignKey('Policy', models.CASCADE)

    action_codename = 'policykitchangeconstitutionpolicy'

    def __str__(self):
        return "Change Constitution Policy: " + self.name

    def execute(self):
        assert self.constitution_policy.kind == Policy.CONSTITUTION
        self.constitution_policy.name = self.name
        self.constitution_policy.description = self.description
        self.constitution_policy.filter = self.filter
        self.constitution_policy.initialize = self.initialize
        self.constitution_policy.check = self.check
        self.constitution_policy.notify = self.notify
        self.constitution_policy.success = self.success
        self.constitution_policy.fail = self.fail
        self.constitution_policy.save()

    class Meta:
        permissions = (
            ('can_execute_policykitchangeconstitutionpolicy', 'Can execute policykit change constitution policy'),
        )

class PolicykitRemovePlatformPolicy(ConstitutionAction):
    platform_policy = models.ForeignKey('Policy',
                                         models.SET_NULL,
                                         null=True)

    action_codename = 'policykitremoveplatformpolicy'

    def __str__(self):
        if self.platform_policy:
            return "Remove Platform Policy: " + self.platform_policy.name
        return "Remove Platform Policy: [ERROR: platform policy not found]"

    def execute(self):
        assert self.platform_policy.kind == Policy.PLATFORM
        self.platform_policy.is_active = False
        self.platform_policy.save()

    class Meta:
        permissions = (
            ('can_execute_policykitremoveplatformpolicy', 'Can execute policykit remove platform policy'),
        )

class PolicykitRecoverPlatformPolicy(ConstitutionAction):
    platform_policy = models.ForeignKey('Policy',
                                         models.SET_NULL,
                                         null=True)

    action_codename = 'policykitrecoverplatformpolicy'

    def __str__(self):
        if self.platform_policy:
            return "Recover Platform Policy: " + self.platform_policy.name
        return "Recover Platform Policy: [ERROR: platform policy not found]"

    def execute(self):
        assert self.platform_policy.kind == Policy.PLATFORM
        self.platform_policy.is_active = True
        self.platform_policy.save()

    class Meta:
        permissions = (
            ('can_execute_policykitrecoverplatformpolicy', 'Can execute policykit recover platform policy'),
        )

class PolicykitRemoveConstitutionPolicy(ConstitutionAction):
    constitution_policy = models.ForeignKey('Policy',
                                            models.SET_NULL,
                                            null=True)

    action_codename = 'policykitremoveconstitutionpolicy'

    def __str__(self):
        if self.constitution_policy:
            return "Remove Constitution Policy: " + self.constitution_policy.name
        return "Remove Constitution Policy: [ERROR: constitution policy not found]"

    def execute(self):
        assert self.constitution_policy.kind == Policy.CONSTITUTION
        self.constitution_policy.is_active = False
        self.constitution_policy.save()

    class Meta:
        permissions = (
            ('can_execute_policykitremoveconstitutionpolicy', 'Can execute policykit remove constitution policy'),
        )

class PolicykitRecoverConstitutionPolicy(ConstitutionAction):
    constitution_policy = models.ForeignKey('Policy',
                                            models.SET_NULL,
                                            null=True)

    action_codename = 'policykitrecoverconstitutionpolicy'

    def __str__(self):
        if self.constitution_policy:
            return "Recover Constitution Policy: " + self.constitution_policy.name
        return "Recover Constitution Policy: [ERROR: constitution policy not found]"

    def execute(self):
        assert self.constitution_policy.kind == Policy.CONSTITUTION
        self.constitution_policy.is_active = True
        self.constitution_policy.save()

    class Meta:
        permissions = (
            ('can_execute_policykitrecoverconstitutionpolicy', 'Can execute policykit recover constitution policy'),
        )

class PlatformAction(BaseAction, PolymorphicModel):
    ACTION = None
    AUTH = 'app'
    action_kind = ActionKind.PLATFORM

    community_revert = models.BooleanField(default=False)
    """True if the action has been reverted on the platform."""

    community_origin = models.BooleanField(default=False)
    """True if the action originated on the platform."""

    action_type = "PlatformAction" #TODO DELETE

    readable_name = '' #TODO delete
    """Readable name of the action type."""

    class Meta:
        verbose_name = 'platformaction'
        verbose_name_plural = 'platformactions'

    def __str__(self):
        if self.readable_name and self.community.platform:
            return f"{self.community.platform} {self.readable_name}"
        return self.action_type_new or super(PlatformAction, self).__str__() #TODO: we want the PK sometimes..

    def revert(self, values, call, method=None):
        """
        Reverts the action.
        """
        _ = LogAPICall.make_api_call(self.community, values, call, method=method)
        self.community_revert = True
        self.save()

    def execute(self):
        """
        Executes the action.
        """
        self.community.execute_platform_action(self)

class PlatformActionBundle(BaseAction):
    ELECTION = 'election'
    BUNDLE = 'bundle'
    BUNDLE_TYPE = [
        (ELECTION, 'election'),
        (BUNDLE, 'bundle')
    ]
    action_type = "PlatformActionBundle" #TODO delete
    action_kind = ActionKind.PLATFORM

    bundled_actions = models.ManyToManyField(PlatformAction)
    bundle_type = models.CharField(choices=BUNDLE_TYPE, max_length=10)

    def execute(self):
        if self.bundle_type == PlatformActionBundle.BUNDLE:
            for action in self.bundled_actions.all():
                self.community.execute_platform_action(action)

    class Meta:
        verbose_name = 'platformactionbundle'
        verbose_name_plural = 'platformactionbundles'

class PlatformPolicyManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(kind=Policy.PLATFORM)

class ConstitutionPolicyManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(kind=Policy.CONSTITUTION)

class Policy(models.Model):
    """Policy"""

    PLATFORM = 'platform'
    CONSTITUTION = 'constitution'
    POLICY_KIND = [
        (PLATFORM, 'platform'),
        (CONSTITUTION, 'constitution')
    ]

    FILTER = 'filter'
    INITIALIZE = 'initialize'
    CHECK = 'check'
    NOTIFY = 'notify'
    SUCCESS = 'success'
    FAIL = 'fail'

    kind = models.CharField(choices=POLICY_KIND, max_length=30)
    """Kind of policy (platform or constitution)."""

    filter = models.TextField(blank=True, default='')
    """The filter code of the policy."""

    initialize = models.TextField(blank=True, default='')
    """The initialize code of the policy."""

    check = models.TextField(blank=True, default='')
    """The check code of the policy."""

    notify = models.TextField(blank=True, default='')
    """The notify code of the policy."""

    success = models.TextField(blank=True, default='')
    """The pass code of the policy."""

    fail = models.TextField(blank=True, default='')
    """The fail code of the policy."""

    community = models.ForeignKey(CommunityPlatform,
        models.CASCADE,
        verbose_name='community',
    )
    """The community which the policy belongs to."""

    name = models.CharField(max_length=100)
    """The name of the policy."""

    description = models.TextField(null=True, blank=True)
    """The description of the policy. May be empty."""

    is_active = models.BooleanField(default=True)
    """True if the policy is active. Default is True."""

    modified_at = models.DateTimeField(auto_now=True)
    """Datetime object representing the last time the policy was modified."""

    # TODO(https://github.com/amyxzhang/policykit/issues/341) add back support for policy bundles
    bundled_policies = models.ManyToManyField("self", blank=True, symmetrical=False, related_name="member_of_bundle")
    """Policies bundled inside this policy."""

    # Managers
    objects = models.Manager()
    platform_policies = PlatformPolicyManager()
    constitution_policies = ConstitutionPolicyManager()

    class Meta:
        abstract = False

    def __str__(self):
        prefix = "PlatformPolicy: " if self.kind == self.PLATFORM else "ConstitutionPolicy: "
        return prefix + self.name

    def save(self, *args, **kwargs):
        if not self.name:
            raise ValidationError("Name is required.")
        super(Policy, self).save(*args, **kwargs)

    @property
    def is_bundled(self):
        """True if the policy is part of a bundle"""
        return self.member_of_bundle.count() > 0


class UserVote(models.Model):
    """UserVote"""

    user = models.ForeignKey(CommunityUser, models.CASCADE)
    """The user who cast the vote."""

    evaluation = models.ForeignKey(PolicyEvaluation, models.CASCADE)
    """The policy evaluation that initiated the vote."""

    vote_time = models.DateTimeField(auto_now_add=True)
    """Datetime object representing when the vote was cast."""

    class Meta:
        abstract = True

    def get_time_elapsed(self):
        """
        Returns a datetime object representing the time elapsed since the vote was cast.
        """
        return datetime.now(timezone.utc) - self.vote_time

class BooleanVote(UserVote):
    """BooleanVote"""

    TRUE_FALSE_CHOICES = (
        (True, 'Yes'),
        (False, 'No')
    )
    boolean_value = models.BooleanField(
        null=True,
        choices=TRUE_FALSE_CHOICES,
        default=True
    )
    """The value of the vote. Either True ('Yes') or False ('No')."""

    def __str__(self):
        return str(self.user) + ' : ' + str(self.boolean_value)

class NumberVote(UserVote):
    """NumberVote"""

    number_value = models.IntegerField(null=True)
    """The value of the vote. Must be an integer."""

    def __str__(self):
        return str(self.user) + ' : ' + str(self.number_value)

class PlatformActionForm(ModelForm):
    class Meta:
        model = PlatformAction
        exclude = [
            "initiator",
            "community",
            "community_revert",
            "community_origin",
            "is_bundled",
            "community_post"
        ]

    def __init__(self, *args, **kwargs):
        super(PlatformActionForm, self).__init__(*args, **kwargs)
        self.label_suffix = ''
