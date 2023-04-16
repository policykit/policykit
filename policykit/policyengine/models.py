import json
import logging
from datetime import datetime, timezone

from actstream import action as actstream_action
from django.contrib.auth.models import Group, User, UserManager
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.deletion import CASCADE
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.forms import ModelForm
from metagov.core.models import GovernanceProcess
from polymorphic.models import PolymorphicManager, PolymorphicModel

import policyengine.utils as Utils
from policyengine import engine
from policyengine.metagov_app import metagov

logger = logging.getLogger(__name__)


class PolicyActionKind:
    PLATFORM = "platform"
    CONSTITUTION = "constitution"
    TRIGGER = "trigger"


class Community(models.Model):
    """A Community represents a group of users. They may exist on one or more online platforms."""

    metagov_slug = models.SlugField(max_length=36, unique=True, null=True, blank=True)

    def __str__(self):
        prefix = super().__str__()
        return '{} {}'.format(prefix, self.community_name)

    @property
    def community_name(self):
        return self.constitution_community.community_name if self.constitution_community else ''

    def get_roles(self):
        """
        Returns a QuerySet of all roles in the community.
        """
        return CommunityRole.objects.filter(community=self)

    def get_policies(self, is_active=True):
        return Policy.objects.filter(community=self, is_active=is_active).order_by('-modified_at')

    def get_platform_policies(self, is_active=True):
        """
        Returns a QuerySet of all platform policies in the community.
        """
        return Policy.platform_policies.filter(community=self, is_active=is_active).order_by('-modified_at')

    def get_constitution_policies(self, is_active=True):
        """
        Returns a QuerySet of all constitution policies in the community.
        """
        return Policy.constitution_policies.filter(community=self, is_active=is_active).order_by('-modified_at')

    def get_trigger_policies(self, is_active=True):
        """
        Returns a QuerySet of all trigger policies in the community.
        """
        return Policy.objects.filter(community=self, kind=Policy.TRIGGER, is_active=is_active).order_by('-modified_at')

    def get_documents(self, is_active=True):
        """
        Returns a QuerySet of all documents in the community.
        """
        return CommunityDoc.objects.filter(community=self, is_active=is_active)

    @property
    def constitution_community(self):
        from constitution.models import ConstitutionCommunity
        return ConstitutionCommunity.objects.filter(community=self).first()

    def get_platform_communities(self):
        constitution_community = self.constitution_community
        return CommunityPlatform.objects.filter(community=self).exclude(pk=constitution_community.pk)

    def get_platform_community(self, name: str):
        for p in CommunityPlatform.objects.filter(community=self):
            if p.platform == name:
                return p
        return None

    def save(self, *args, **kwargs):
        """
        Saves the Community. If community is new, creates it in Metagov and stores the Metagov-generated slug.

        :meta private:
        """
        is_new = True if not self.pk else False
        if is_new and not self.metagov_slug:
            # If this is the first save, create a corresponding community in Metagov
            mg_community = metagov.create_community()
            self.metagov_slug = mg_community.slug
            # logger.debug(f"Created new Metagov community '{self.metagov_slug}' Saving slug in model.")

        super(Community, self).save(*args, **kwargs)

class CommunityPlatform(PolymorphicModel):
    """A CommunityPlatform represents a group of users on a single platform."""

    platform = None
    """The name of the platform ('Slack', 'Reddit', etc.)."""

    community_name = models.CharField('team_name', max_length=1000)
    """The name of the community."""

    community = models.ForeignKey(Community, on_delete=models.CASCADE)
    """The ``Community`` that this CommunityPlatform belongs to."""

    def __str__(self):
        return self.community_name

    @property
    def metagov_slug(self):
        return self.community.metagov_slug

    @property
    def metagov_plugin(self):
        mg_community = metagov.get_community(self.metagov_slug)
        team_id = getattr(self, "team_id", None)
        return mg_community.get_plugin(self.platform, community_platform_id=team_id)

    def initiate_vote(self, proposal, users=None):
        """
        Initiates a vote on whether to pass the action that is currently being evaluated.

        Parameters
        -------
        proposal
            The ``Proposal`` that is being run.
        users
        The users who should be notified.
        """
        pass

    def get_roles(self):
        """
        Returns a QuerySet of all roles in the community.
        """
        return self.community.get_roles()

    def get_users(self, role_names=None):
        """
        Returns a QuerySet of all users in the community on this platform.
        """
        if role_names:
            # Not efficient, we are doing two queries in order to filter by 'role_name'
            # because it is a field on CommunityRole, but not on Group.
            roles = self.community.get_roles().filter(role_name__in=role_names)
            return CommunityUser.objects.filter(community=self, groups__in=roles).distinct()

        return CommunityUser.objects.filter(community=self)


    def _execute_platform_action(self):
        pass

    def save(self, *args, **kwargs):
        if not self.pk and not hasattr(self, "community"):
            # This is the first platform, so create the parent Community
            self.community = Community.objects.create()

        if not self.pk and not self.platform == "constitution":
            from constitution.models import ConstitutionCommunity
            ConstitutionCommunity.objects.get_or_create(
                community=self.community,
                defaults={'community_name': self.community_name}
            )

        super(CommunityPlatform, self).save(*args, **kwargs)

class CommunityRole(Group):
    """CommunityRole"""

    community = models.ForeignKey(Community, models.CASCADE)
    """The community which the role belongs to."""

    role_name = models.TextField('readable_name', max_length=300)
    """The readable name of the role."""

    description = models.TextField(null=True, blank=True, default='')
    """The readable description of the role. May be empty."""

    is_base_role = models.BooleanField(default=False)
    """Whether this is the default role in this community."""

    def __str__(self):
        return str(self.role_name)

    def save(self, *args, **kwargs):

        # Generate a unique group name
        self.name = f"{self.community} : {self.role_name}"

        if self.is_base_role:
            """
            Enforce that each community only has one base role.
            """
            try:
                temp = CommunityRole.objects.get(community=self.community, is_base_role=True)
                if self != temp:
                    raise ValidationError("Cannot add new base role to community")
            except CommunityRole.DoesNotExist:
                pass

        super(CommunityRole, self).save(*args, **kwargs)

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

    def find_linked_username(self, platform):
        mg_community = metagov.get_community(self.community.metagov_slug)
        from metagov.core import identity

        users = identity.get_users(
            community=mg_community,
            platform_type=self.community.platform,
            community_platform_id=self.community.team_id,
            platform_identifier=self.username
        )
        logger.debug(f"Users linked to {self}: {users}")
        if len(users) > 1:
            raise Exception("More than 1 matching user found")
        if len(users) == 1:
            for account in users[0]["linked_accounts"]:
                if account["platform_type"] == platform:
                    return account["platform_identifier"]
        return None

    def get_roles(self):
        """
        Returns a list of CommunityRoles containing all of the user's roles.
        """
        user_roles = []
        for r in self.community.get_roles():
            for u in r.user_set.all():
                if u.communityuser.username == self.username:
                    user_roles.append(r)
        return user_roles

    def has_role(self, name):
        """
        Returns True if the user has a role with the specified role_name.

        Parameters
        -------
        name
            The name of the role to check for.
        """
        return self.groups.filter(communityrole__role_name=name).exists()


    @property
    def constitution_community(self):
        """
        The ConstitutionCommunity that this user belongs to.
        """
        from constitution.models import ConstitutionCommunity
        return ConstitutionCommunity.objects.get(community=self.community.community)

    def save(self, *args, **kwargs):
        """
        Saves the user. Note: Only meant for internal use.

        :meta private:
        """
        super(CommunityUser, self).save(*args, **kwargs)

        community = self.community.community # parent community, not platform community.

        # Add user to the base role for this Community.
        # Use "get_or_create" because there might not be a base role yet, if this is a brand new community and a StarterKit has not been selected yet.
        # In that case, the StarterKit will override this base_role when it gets initialized.
        base_role,_ = CommunityRole.objects.get_or_create(community=community, is_base_role=True, defaults={"role_name": "Base Role"})
        base_role.user_set.add(self)

        # Call get_or_create integration admin on each save to ensure that it gets created, even if installer is not a community admin
        integration_admin_role = Utils.get_or_create_integration_admin_role(community)

        # If this user is an admin in the community, give them access to add and remove integrations
        if self.is_community_admin:
            integration_admin_role.user_set.add(self)


class CommunityDoc(models.Model):
    """CommunityDoc"""

    name = models.TextField(null=True, blank=True, default = '')
    """The name of the document."""

    text = models.TextField(null=True, blank=True, default = '')
    """The text within the document."""

    community = models.ForeignKey(Community, models.CASCADE)
    """The community which the document belongs to."""

    is_active = models.BooleanField(default=True)
    """True if the document is active. Default is True."""

    def __str__(self):
        return str(self.name)


class DataStore(models.Model):
    """DataStore used for persisting serializable data on a Proposal."""

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
    """
    Stores a record of an API call being made, and calls on the CommunityPlatform to make the API call.
    The purpose of storing this is so that we can match them with incoming events to see if the event
    originated from a PolicyKit call.

    For example, say PolicyKit made a Slack post on behalf of a user. A moment later, we can an event notification
    from Slack about that new post. We look back at recent LogAPICalls to see if the post was made by us. If it
    was, we ignore the event.
    """
    community = models.ForeignKey(CommunityPlatform, models.CASCADE)
    proposal_time = models.DateTimeField(auto_now_add=True)
    call_type = models.CharField('call_type', max_length=300)
    # JSON blob of the request payload, which is used for matching the incoming event with recent requests.
    extra_info = models.TextField()

    def __str__(self):
        return f"LogAPICall {self.call_type} ({self.pk})"

    @classmethod
    def make_api_call(cls, community, values, call, action=None, method=None):
        LogAPICall.objects.create(
            community=community,
            call_type=call,
            extra_info=json.dumps(values)
        )
        return community.make_call(call, values=values, action=action, method=method)

class Proposal(models.Model):
    """The Proposal model represents the evaluation of a particular policy for a particular action.
    All data relevant to the evaluation, such as vote counts, is stored in this model."""

    PROPOSED = 'proposed'
    FAILED = 'failed'
    PASSED = 'passed'
    STATUS = [
        (PROPOSED, 'proposed'),
        (FAILED, 'failed'),
        (PASSED, 'passed')
    ]

    proposal_time = models.DateTimeField(auto_now_add=True)
    """Datetime object representing when the proposal was created."""

    status = models.CharField(choices=STATUS, max_length=10)
    """Status of the proposal. One of PROPOSED, PASSED or FAILED."""

    policy = models.ForeignKey('Policy', on_delete=models.SET_NULL, editable=False, blank=True, null=True)
    """The policy that is being evaluated."""

    action = models.ForeignKey('BaseAction', on_delete=models.CASCADE, editable=False)
    """The action that triggered the proposal."""

    data = models.OneToOneField(DataStore, models.CASCADE, null=True, blank=True)
    """Datastore for persisting any additional data related to the proposal."""

    vote_post_id = models.CharField(max_length=300, blank=True)
    """Platform identifier of the voting post, if any."""

    governance_process = models.ForeignKey(GovernanceProcess, on_delete=models.SET_NULL, blank=True, null=True)
    """The Metagov GovernanceProcess that is being used to make a decision about this Proposal, if any."""

    def __str__(self):
        return f"Proposal {self.pk}: {self.action} : {self.policy or 'POLICY_DELETED'} ({self.status})"

    @property
    def vote_url(self):
        """
        The URL of the vote associated with this policy evaluation, if any.
        """
        if self.governance_process:
            return self.governance_process.url
        return None

    @property
    def is_vote_closed(self):
        """
        Returns True if the vote is closed, False if the vote is still open.
        """
        if self.governance_process:
            return self.governance_process.status == "completed"
        return self.status != Proposal.PROPOSED

    def get_time_elapsed(self):
        """
        Returns a datetime object representing the time elapsed since the first proposal.
        """
        return datetime.now(timezone.utc) - self.proposal_time

    def get_all_boolean_votes(self, users=None):
        """
        For Boolean voting. Returns all boolean votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.
        """
        if users:
            return BooleanVote.objects.filter(proposal=self, user__in=users)
        return BooleanVote.objects.filter(proposal=self)

    def get_choice_votes(self, value=None):
        if value:
            return ChoiceVote.objects.filter(proposal=self, value=value)
        return ChoiceVote.objects.filter(proposal=self)

    def get_yes_votes(self, users=None):
        """
        For Boolean voting. Returns the yes votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.
        """
        if users:
            return BooleanVote.objects.filter(boolean_value=True, proposal=self, user__in=users)
        return BooleanVote.objects.filter(boolean_value=True, proposal=self)

    def get_no_votes(self, users=None):
        """
        For Boolean voting. Returns the no votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.
        """
        if users:
            return BooleanVote.objects.filter(boolean_value=False, proposal=self, user__in=users)
        return BooleanVote.objects.filter(boolean_value=False, proposal=self)

    def get_all_number_votes(self, users=None):
        """
        For Number voting. Returns all number votes as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.
        """
        if users:
            return NumberVote.objects.filter(proposal=self, user__in=users)
        return NumberVote.objects.filter(proposal=self)

    def get_one_number_votes(self, value, users=None):
        """
        For Number voting. Returns number votes for the specified value as a QuerySet. Can specify a subset of users to count votes of. If no subset is specified, then votes from all users will be counted.
        """
        if users:
            return NumberVote.objects.filter(number_value=value, proposal=self, user__in=users)
        return NumberVote.objects.filter(number_value=value, proposal=self)

    def save(self, *args, **kwargs):
        """
        Saves the proposal. Note: Only meant for internal use.

        :meta private:
        """
        if not self.pk:
            self.data = DataStore.objects.create()
        super(Proposal, self).save(*args, **kwargs)

    def _pass_evaluation(self):
        """
        Sets the proposal to PASSED.

        :meta private:
        """
        self.status = Proposal.PASSED
        self.save()
        action = self.action
        actstream_action.send(action, verb='was passed', community_id=action.community.id, action_codename=action.action_type)
        if self.governance_process:
            try:
                self.governance_process.proxy.close()
            except NotImplementedError:
                pass
    def _fail_evaluation(self):
        """
        Sets the proposal to FAILED.

        :meta private:
        """
        self.status = Proposal.FAILED
        self.save()
        action = self.action
        actstream_action.send(action, verb='was failed', community_id=action.community.id, action_codename=action.action_type)
        if self.governance_process:
            try:
                self.governance_process.proxy.close()
            except NotImplementedError:
                pass

class BaseAction(PolymorphicModel):
    """Base Action"""

    community = models.ForeignKey(CommunityPlatform, models.CASCADE, verbose_name='community')
    """The ``CommunityPlatform`` in which the action occurred (or was proposed). If proposed through the PolicyKit app,
    this is the community that the proposing user was authenticated with."""

    initiator = models.ForeignKey(CommunityUser, models.CASCADE, blank=True, null=True)
    """The ``CommunityUser`` who initiated the action. May not exist if initiated by PolicyKit."""

    is_bundled = models.BooleanField(default=False)
    """True if the action is part of a bundle."""

    kind = None
    """Kind of action. One of 'platform' or 'constitution' or 'trigger'. Do not override."""

    data_store = models.OneToOneField(DataStore, models.CASCADE, null=True, blank=True)
    """Datastore for persisting any additional data related to the proposal."""

    def __str__(self):
        return f"{self._meta.verbose_name.title()} ({self.pk})"

    @property
    def action_type(self):
        """The type of action (such as 'slackpostmessage' or 'policykitaddcommunitydoc')."""
        return self._meta.model_name

    @property
    def _is_reversible(self):
        if self.kind in [PolicyActionKind.TRIGGER, PolicyActionKind.CONSTITUTION]:
            return False
        return self.kind == PolicyActionKind.PLATFORM and self.community_origin

    @property
    def _is_executable(self):
        if self.kind == PolicyActionKind.TRIGGER:
            # Trigger actions can never be executed
            return False

        if self.kind == PolicyActionKind.CONSTITUTION:
            # Constitution actions can always be executed
            return True

        if self.kind == PolicyActionKind.PLATFORM and not self.community_origin:
            # Governable platform actions proposed in the PolicyKit UI can be executed.
            return True

        if self.kind == PolicyActionKind.PLATFORM and self.community_origin and self.community_revert:
            # Governable platform actions that originated on the platform and have previously reverted, can be executed.
            return True

        return False


class GovernableAction(BaseAction, PolymorphicModel):
    """
    Governable action that can be executed and reverted. Constitution actions are governable.
    """
    kind = PolicyActionKind.PLATFORM # should only by overridden by constitiiution app

    ACTION = None
    AUTH = 'app'


    community_revert = models.BooleanField(default=False)
    """True if the action has been reverted."""

    community_origin = models.BooleanField(default=False)
    """True if the action originated on an external platform. False if the action originated in PolicyKit, either from a Policy or being proposed in the PolicyKit web interface."""

    def save(self, *args, **kwargs):
        """
        Saves the governable action. If new, evaluates against current policies.

        :meta private:
        """
        evaluate_action = kwargs.pop("evaluate_action", None)
        should_evaluate = (not self.pk and evaluate_action != False) or evaluate_action

        if should_evaluate:
            can_propose_perm = f"{self._meta.app_label}.add_{self.action_type}"
            can_execute_perm = f"{self._meta.app_label}.can_execute_{self.action_type}"

            if self.initiator and self.initiator.has_perm(can_execute_perm):
                self.execute()  # No `Proposal` is created because we don't evaluate it
                super(GovernableAction, self).save(*args, **kwargs)
                ExecutedActionTriggerAction.from_action(self).evaluate()

            elif self.initiator and not self.initiator.has_perm(can_propose_perm):
                if self._is_reversible:
                    logger.debug(f"{self.initiator} does not have permission to propose action {self.action_type}: reverting")
                    super(GovernableAction, self).save(*args, **kwargs)
                    self._revert()
                    actstream_action.send(self, verb='was reverted due to lack of permissions', community_id=self.community.id, action_codename=self.action_type)
                else:
                    logger.debug(f"{self.initiator} does not have permission to propose action {self.action_type}: doing nothing")

            else:
                super(GovernableAction, self).save(*args, **kwargs)

                proposal = engine.evaluate_action(self)
                if proposal and proposal.status == Proposal.PASSED:
                    # Evaluate a trigger for the acion being executed
                    ExecutedActionTriggerAction.from_action(self).evaluate()

        super(GovernableAction, self).save(*args, **kwargs)

    def _revert(self, values=None, call=None, method=None):
        """
        Reverts the action.
        """
        if call:
            LogAPICall.make_api_call(self.community, values or {}, call, method=method)
        self.community_revert = True
        self.save()

    def execute(self):
        """
        Executes the action.
        """
        self.community._execute_platform_action(self)


class TriggerAction(BaseAction, PolymorphicModel):
    """Trigger Action"""
    kind = PolicyActionKind.TRIGGER

    class Meta:
        abstract = True

    def evaluate(self):
        return engine.evaluate_action(self)


class ExecutedActionTriggerAction(TriggerAction):
    """Represents a GovernableAction that has passed"""
    action = models.ForeignKey(GovernableAction, on_delete=CASCADE)

    @staticmethod
    def from_action(action):
        return ExecutedActionTriggerAction(
            action=action,
            community=action.community,
            initiator=action.initiator
        )

    def __str__(self):
        return f"Trigger: {self.action._meta.verbose_name.title()} ({self.pk})"


class WebhookTriggerAction(TriggerAction):
    """Represents a Trigger action from any webhook event.
    Data about the event can be accessed through the data property."""
    event_type = models.CharField(max_length=50, blank=True, null=True)
    data = models.JSONField(blank=True, null=True)
    #add platform_name "source"
    #add platform_community_platform_id

    def __str__(self):
        return f"Trigger: {self.event_type} ({self.pk})"

class PlatformPolicyManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(kind=Policy.PLATFORM)

class ConstitutionPolicyManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(kind=Policy.CONSTITUTION)

class ActionType(models.Model):
    """The action_type of a BaseAction"""

    codename = models.CharField(max_length=30, unique=True)

class PolicyVariable(models.Model):
    """Policy Variable"""

    NUMBER = 'number'
    STRING = 'string'

    POLICY_VARIABLE_TYPE = [
        (NUMBER, 'number'),
        (STRING, 'string')
    ]

    name = models.CharField(blank=False, max_length=100)
    """The name of the variable."""

    label = models.CharField(blank=False, max_length=100)
    """The label used in public facing forms."""

    default_value = models.CharField(blank=False, max_length=100)
    """The deafult value assigned to the variable."""

    is_required = models.BooleanField(default=False)
    """Whether a value for this policy variable is required."""

    value = models.CharField(blank=True, max_length=100)
    """The value assigned to the variable."""

    prompt = models.CharField(blank=True, max_length=255)
    """Help text used in public facing forms."""

    type = models.CharField(choices=POLICY_VARIABLE_TYPE, max_length=30, default=STRING)
    """Variable type, which should correlate to form ui element."""

    is_list = models.BooleanField(default=False)
    """Whether the variable is a list. If it is a list of strings or numbers, then they are comma separated without brackets."""

    entity = models.CharField(blank=True, null=True, max_length=100)

    policy = models.ForeignKey("Policy", related_name="variables", on_delete=models.CASCADE)
    """Variables used in the scope of the policy."""

    def clean(self):
        if self.is_required and not self.value:
            raise ValidationError('Variable value is required')

class Policy(models.Model):
    """Policy"""

    PLATFORM = 'platform'
    CONSTITUTION = 'constitution'
    TRIGGER = 'trigger'
    POLICY_KIND = [
        (PLATFORM, 'platform'),
        (CONSTITUTION, 'constitution'),
        (TRIGGER, 'trigger')
    ]

    FILTER = 'filter'
    INITIALIZE = 'initialize'
    CHECK = 'check'
    NOTIFY = 'notify'
    SUCCESS = 'success'
    FAIL = 'fail'

    kind = models.CharField(choices=POLICY_KIND, max_length=30)
    """Kind of policy (platform, constitution, or trigger)."""

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

    community = models.ForeignKey(Community, models.CASCADE, null=True)
    """The community which the policy belongs to."""

    action_types = models.ManyToManyField(ActionType)
    """The action types that this policy applies to."""

    name = models.CharField(max_length=100)
    """The name of the policy."""

    description = models.TextField(null=True, blank=True)
    """The description of the policy. May be empty."""

    is_active = models.BooleanField(default=True)
    """True if the policy is active. Default is True."""

    is_template = models.BooleanField(default=False)
    """True if the policy can be used as a template for other policies. Default is False."""

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
        return f"{self.kind.capitalize()} Policy: {self.name}"

    @property
    def is_bundled(self):
        """True if the policy is part of a bundle"""
        return self.member_of_bundle.count() > 0

    def save(self, *args, **kwargs):
        if not self.is_template and self.community is None:
            raise ValidationError('Non template policies must have a community')

        super(Policy, self).save(*args, **kwargs)

    def update_variables(self, variable_data = {}):
        """Update related variables based on dict"""

        # Cast keys in variable_data to integars
        variable_data = { int(k): v for k,v in variable_data.items() }

        # Make copies of related PolicyVariables
        for variable in self.variables.all():
            # variable_data is an object in shape of { [pk] : [value] }
            if variable.pk in variable_data:
                # Set the value of the new variable based on variable_data
                variable.value = variable_data[variable.pk]

            variable.save()

    def copy_as_template(self, variable_data = {}):
        """Make a copy of the policy object and designate it as a template"""

        from copy import deepcopy

        # Make a copy of the whole object
        new_policy = deepcopy(self)

        # Generate a new id
        new_policy.pk = None

        # Treat new policy as a template as to not requiring a community relationship yet
        new_policy.is_template = True

        # Save new policy
        new_policy.save()

        # Copy ActionType relationships
        new_policy.action_types.set(self.action_types.all())

        # Remove existing Policy Variable relationships
        new_policy.variables.set([])

        # Cast keys in variable_data to integars
        variable_data = { int(k): v for k,v in variable_data.items() }

        # Make copies of related PolicyVariables
        for variable in self.variables.all():
            new_variable = deepcopy(variable)
            new_variable.pk = None
            new_variable.policy = new_policy

            # variable_data is an object in shape of { [pk] : [value] }
            if variable.pk in variable_data:
                # Set the value of the new variable based on variable_data
                new_variable.value = variable_data[variable.pk]
            else:
                # Set the value of the new variable based on the original variable's default_value
                new_variable.value = variable.default_value

            new_variable.save()

        return new_policy

    def copy_to_community(self, community = None, variable_data = {}):
        """Make a copy of the policy object and assign to a new community"""


        # TODO NMV Feb 1: revert this after a UI is added to make Template Policies
        # if not self.is_template:
        #     raise Exception("Policy is not a template")

        if not community:
            raise Exception("Community object must be passed")

        # Generate a copy of the policy
        new_policy = self.copy_as_template(variable_data)

        # Designate policy as not-a-template
        new_policy.is_template = False

        # Assign copy to another community
        new_policy.community = community

        # Save
        new_policy.save()

        return new_policy

class UserVote(models.Model):
    """UserVote"""

    user = models.ForeignKey(CommunityUser, models.CASCADE)
    """The user who cast the vote."""

    proposal = models.ForeignKey(Proposal, models.CASCADE)
    """The policy proposal that initiated the vote."""

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

class ChoiceVote(UserVote):
    """ChoiceVote"""

    value = models.CharField(max_length=100)
    """The value of the vote."""

    def __str__(self):
        return str(self.user) + ' : ' + str(self.value)

class NumberVote(UserVote):
    """NumberVote"""

    number_value = models.IntegerField(null=True)
    """The value of the vote. Must be an integer."""

    def __str__(self):
        return str(self.user) + ' : ' + str(self.number_value)

class GovernableActionForm(ModelForm):
    class Meta:
        model = GovernableAction
        exclude = [
            "initiator",
            "community",
            "community_revert",
            "community_origin",
            "is_bundled"
        ]

    def __init__(self, *args, **kwargs):
        super(GovernableActionForm, self).__init__(*args, **kwargs)
        self.label_suffix = ''

class CustomAction(models.Model):
    
    JSON_FIELDS = ["filter"]
    """fields that are stored as JSON dumps"""

    action_type = models.ForeignKey(ActionType, on_delete=models.CASCADE)
    """actions that this custom action is built upon"""

    is_trigger = models.BooleanField(default=False)
    """ whether this action should be treated as triggers or governable actions """

    filter = models.TextField(blank=True, default="[]")
    """
        a JSON object. For each custom action, we only allow filters that apply to the filter parameters 
        defined in the referenced governable action. See examples of filter modules in policytemplates/filters.json
        e.g.,
        {
            "initiator": {
                "kind": "CommunityUser", 
                "name": "permission",
                "codes": "...",
                "variables": [
                    {
                        "name": "permission",
                        "type": "string",
                        "value": "can_add_slackpostmessage"
                    }
                ]
            },
            "text": {
                "kind": "Text", 
                "name": "startsWtih",
                "codes": "...",
                "variables": [
                    {
                        "name": "word",
                        "type": "string",
                        "value": "vote"
                    }
                ]
            },
            "channel": null,
            "timestamp": null
        }
    """

    community_name = models.TextField(null=True, unique=True)
    """
        If users think this ActionFilter is frequently used, then they can name this filter 
            and we would show it in the CustomAction tab on the interface.
        
        When it is null it means that users do not think it is frequently used;
        We require it to be unique so that their permission codenames won't be the same
    """
        
    @property
    def action_kind(self):
        """ get the corresponding policy kind: PLATFORM, CONSTITUTION or TRIGGER """
        if self.is_trigger:
            return Policy.TRIGGER
        else:
            action_class = Utils.find_action_cls(self.action_type.codename)
            app_label = action_class._meta.app_label
            if app_label == "constitution":
                return Policy.CONSTITUTION
            else:
                return Policy.PLATFORM
                
    def loads(self, attr):
        """ load a field that is stored as a JSON dump """
        return json.loads(getattr(self, attr))
    
    def dumps(self, attr, value):
        """ set a field, which is stored as a JSON dump, as the given value """
        setattr(self, attr, json.dumps(value))
    
    def to_json(self):
        """ return a json object that represents this filter """
        return {
            "action_type": self.action_type.codename,
            "filter": self.loads("filter"),
            "community_name": self.community_name
        }
    
    @property
    def permissions(self):
        if self.community_name:
            # If it is a user custom action, it has a new permission name
            permissions = ((f"can_execute_{self.community_name}", "Can execute {self.community_name}"))
        else:
            from django.contrib.auth.models import Permission
            from django.contrib.contenttypes.models import ContentType

            # Otherwise, this permission for this new CustomAction is the same as the GovernableAction it builts upon 
            action_content_type = ContentType.objects.filter(model=self.action_type)     
            all_permissions = Permission.objects.filter(content_type__in=action_content_type)
            # Search for all permissions related to this GovernableAction
            permissions = [(perm.codename, perm.name) for perm in all_permissions if perm.codename.startswith("can_execute") ]
            
            # While it is obvious that the permission codename is f"can_execute_{self.action_type}", 
            # We actually do not know exactly the corresponding permisson name
            # That is why we take such trouble to extract it
        return permissions


    def save(self, *args, **kwargs):
        """
        Add the permission if it is a user custom action
        """
        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        if not self.pk and self.community_name:
            action_content_type = ContentType.objects.get_for_model(CustomAction)
            all_permissions = self.permissions
            for perm in all_permissions:
                # TODO not sure whether we should use the content type of CustomAction here
                Permission.objects.create(codename=perm[0], name=perm[1], content_type=action_content_type)
                # TODO not sure we would like to assign this permission to all users by default or not
                # perhaps we should at first assign it to users who have the execute permission of the referenced GovernableAction
        super(CustomAction, self).save(*args, **kwargs)

class Procedure(models.Model):

    JSON_FIELDS = ["initialize", "notify", "check", "success", "fail", "variables"]
    """fields that are stored as JSON dumps"""

    SLACK = "Slack"
    DISCORD = "Discord"
    DISCOURSE = "Discourse"
    GITHUB = "Github"
    OPENCOLLECTIVE = "Opencollective"
    REDDIT = "Reddit"
    ALL = "All"
    
    PLATFORMS = [
        (SLACK, "Slack"),
        (DISCORD, "Discord"),
        (DISCOURSE, "Discourse"),
        (GITHUB, "Github"),
        (OPENCOLLECTIVE, "OpenCollective"),
        (REDDIT, "Reddit"),
        (ALL, "All"),
    ]

    class Meta:
        unique_together = ('name', 'platform')
        """
            We will use the name to search for the corresponding procedure, and therefore it should be unique.
            On the other hand, we allow a similar procedure (such as consesus voting) to be used on different platforms.
            Therefore, these two fields combined should be unique.
        """

    name = models.TextField(blank=True, default='')
    """ such as Jury, Dictator, etc. """

    description = models.TextField(blank=True, default='')

    platform = models.TextField(choices=PLATFORMS, blank=True, default='')
    """the platform where the procedure (in particular, the voting component) is expected to happen"""

    initialize = models.TextField(blank=True, default='[]')
    """ ideally we would put the initialization codes of each policy variable here """

    notify = models.TextField(blank=True, default='[]')
    """
        a JSON object. Each list element represents an action that will be executed in the "notify" stage, 
        and its parameters tells us its expected behavior, 
        In partucilar, we could here use variables defined in the "variables" field 
        to specify the parameters of the action
        
        e.g.,
            "notify": [
                {
                    "action": "initiate_vote",
                    "vote_message": "varaibles[\"vote_message\"]",
                    "vote_type": "boolean",
                    "users": "variables[\"dictator\"]",
                    "platform": "slack",
                },
                {
                    "action": "slackpostmessage",
                    "text": "variables[\"notify_message\"]",    
                    "platform": "slack",
                }
            ],

    """

    check = models.TextField(blank=True, default='[]')
    """        
        A JSON object. We execute codes in the `check` field in the order of the list, 
        to make the procedure template simple, we do not support adding new actions at this stage, 
        but users will be asked whether they expect some extra actions happen at this stage when authoring new policies
        e.g.
            "check": [
                {
                    "name": "vote_duration",
                    "codes": "if int(variables[\"duration\"]) > 0:\n  time_elapsed = proposal.get_time_elapsed()\n  if time_elapsed < datetime.timedelta(minutes=int(variables[\"duration\"])):\n    return None\n\n" 
                },
                {
                    "name": "main",
                    "codes": "if not proposal.vote_post_id:\n  return None\n\nyes_votes = proposal.get_yes_votes().count()\nno_votes = proposal.get_no_votes().count()\nif(yes_votes == 1 and no_votes == 0):\n\treturn PASSED\nelif(yes_votes == 0 and no_votes == 1):\n  \treturn FAILED\n\nreturn PROPOSED"
                }
            ]

    """

    success =  models.TextField(blank=True, default='[]')
    """ in a similar structure to the "notify" field  """

    fail =  models.TextField(blank=True, default='[]')
    """ in a similar structure to the "notify" field  """

    variables = models.TextField(blank=True, default='[]')
    """ varaibles used in the procedure """
        
    def loads(self, attr):
        return json.loads(getattr(self, attr))
    
    def to_json(self):
        return {
            "name": self.name,
            "description": self.description,
            "initialize": self.loads("initialize"),
            "notify": self.loads("notify"),
            "check": self.loads("check"),
            "success": self.loads("success"),
            "fail": self.loads("fail"),
        }

class PolicyTemplate(models.Model):

    JSON_FIELDS = ["extra_check", "extra_executions", "variables"]
    """fields that are stored as JSON dumps"""

    name = models.CharField(max_length=100)

    description = models.TextField(null=True, blank=True)

    kind = models.CharField(choices=Policy.POLICY_KIND, max_length=30)
    """Kind of policy template (platform, constitution, or trigger)."""

    custom_actions = models.ManyToManyField(CustomAction)
    """governable actions with filters specified this policy template applies to. """
    
    action_types = models.ManyToManyField(ActionType)
    """The governable actions (with no additional filters specified) that this policy template applies to."""

    is_trigger = models.BooleanField(default=False)
    """
        Whether these actions is treated as triggers;
        this attribute is used together with action_types 
        when users do not create custom actions (which itself stores whether this action is trigger or not).
        But a policy template can govern both custom actions and action types.
    """

    extra_check = models.TextField(blank=True, default='[]')
    """ extra check logic that are preapended to the check logic of the procedure"""

    procedure = models.ForeignKey(Procedure, on_delete=models.CASCADE, null=True)
    """the procedure that this policy template is based on"""

    extra_executions = models.TextField(blank=True, default='{}')
    """
        A JSON object representing extra actions that are expected to be executed in each stage of this policy
        in addition to thoes defined in the referenced procedure.
        While the action item is defined in a similar way to those in the Procedure, 
        we expect to add a new field called "frequency" to actions in the "check" stage 
        to specify how often this action should be executed.

        e.g.,
            {
                "notify": a list of actions,
                "check": [
                    {
                        "action": "slackpostmessage",
                        "text": "we are still waiting for the dictator to make a decision",
                        "frequency": 60,
                    }
                ],
                "success": [],
                "fail": []
            }
    """
    
    variables = models.TextField(blank=True, default='[]')
    """ 
        Varaibles used in all codes of the policy template
        Whenever we add a new module (such as Procedure and CheckModule) 
        that defines its own variables, we will add them here.
    
    """

    def loads(self, attr):
        return json.loads(getattr(self, attr))

    def dumps(self, attr, value):
        setattr(self, attr, json.dumps(value))

    def add_variables(self, new_variables, values={}):
        """
            add new policy variables from other modules or the referenced procedure to this policy template
            
            parameters:
                new_variables:
                    a list of variables to be added, 
                    e.g., 
                        [
                            {
                                "name": "duration",
                                "label": "When the vote is closed (in minutes)",
                                "default_value": 0,
                                "is_required": false,
                                "prompt": "An empty value represents that the vote is closed as long as the success or failure is reached",
                                "type": "number"
                            }
                        ]
    
                values: 
                    a dictionary from each variable name to its specified value if any
                    e.g. 
                        {
                            "duraction": 10, 
                            ...
                        }
        """
        variables = self.loads("variables")
        added_names = [v["name"] for v in variables]
        for var in new_variables:
            # skip variables that have already been added, we assume variables do not have the same name
            if var["name"] in added_names:
                continue
            # set the value of this variable. 
            # We do not check if the value matchs the expected type of the variable now
            if var["name"] in values:
                var["value"] = values[var["name"]]
            else:
                var["value"] = var["default_value"]
            variables.append(var)
        self.dumps("variables", variables)
        self.save()

    def add_check_module(self, check_module):
        """
            add a check module to this policy template
            
            Currently, the variables belonging to this check module is added by calling add_variables explictly
            perhaps we should put them together in the future

            paramters:
                check_module: a CheckModule object

        """

        extra_check = self.loads("extra_check")
        new_check = check_module.to_json()
        # check if the check module has already been added.
        for check in extra_check:
            if check["name"] == new_check["name"]:
                return
        extra_check.append(new_check)
        self.dumps("extra_check", extra_check)
        self.save()

    def add_extra_actions(self, extra_actions):
        """
            add extra actions to this policy template

            Actually we now assume only one action is added at a time 
            because the design of the frontend only allow users to specify one action for each stage

            parameters:
                extra_actions: a dictionary from each stage to a list of actions
                e.g. 
                    {
                        "notify": []
                        "success": [] 
                        "fail": []
                        "check": []
                    }
        """
        extra_executions = self.loads("extra_executions")
        for key in extra_actions:
            if key not in extra_executions:
                extra_executions[key] = []
                # perhaps we would like to use extend in case extra_actions[key] is a list
            extra_executions[key].append(extra_actions[key])
        self.dumps("extra_executions", extra_executions)
        self.save()

    def create_policy_variables(self, policy, variables_data):
        """
            create policy variables for a policy based on this policy template

            parameters:
                policy: the Policy instance that these policy variables are expected to belongs to

                variables_data: a dictionary from each variable name to its value
        """
        variables = self.loads("variables")
        for variable in variables:
            new_variable = PolicyVariable.objects.create(policy=policy, **variable)
            if variable["name"] in variables_data:
                new_variable.value = variables_data[variable["name"]]
            new_variable.save()

    def to_json(self):
        """
            reduce this PolicyTemplate object to a JSON object
        """

        # combine the custom actions and the action types together as a filter of this Procedure    
        filters = [action.to_json() for action in self.custom_actions.all()]
        filters += [{"action_type": action.codename} for action in self.action_types.all()]

        procedure = self.procedure.to_json()
        executions = self.loads("extra_executions")
        # add actions defined in the Procedure isntance to the extra_executions
        for key in ["notify", "success", "fail"]:
            if key not in executions:
                executions[key] = []
            # prepend the procedure actions to the extra_executions
            if key in procedure:
                # We assume extra executions are appended to the procedure actions
                executions[key] = procedure[key] + executions[key]
        if "check" not in executions: # the check in procedure is the check logic instead of executions
            executions["check"] = []

        procedure["check"] = self.loads("extra_check") + procedure["check"]
        return {
            "name": self.name,
            "description": self.description,
            "kind": self.kind,
            "is_trigger": self.is_trigger,
            "filter": filters,
            "check": procedure["check"],
            "executions": executions,
            "variables": self.loads("variables"),
        }
    
    def create_policy(self, community):
        """
            Create a Policy instance based on the JSON object defined by this PolicyTemplate instance
        """
        policy_json = self.to_json()
        policy = Policy.objects.create(name=self.name, description=self.description, kind=self.kind, community=community)
        
        action_types = Utils.extract_action_types(policy_json["filter"]) 
        for action_type in action_types:
            policy.action_types.add(action_type)
        
        policy.filter = Utils.generate_filter_codes(policy_json["filter"])
        policy.initialize = "pass"

        check_executions = Utils.generate_execution_codes(policy_json["executions"]["check"], self.loads("variables"))
        policy.check = check_executions + Utils.generate_check_codes(policy_json["check"])

        policy.notify = Utils.generate_execution_codes(policy_json["executions"]["notify"], self.loads("variables"))
        policy.success = Utils.generate_execution_codes(policy_json["executions"]["success"], self.loads("variables"))
        policy.fail = Utils.generate_execution_codes(policy_json["executions"]["fail"], self.loads("variables"))
        
        self.create_policy_variables(policy, {})
        policy.save()
        return policy

class CheckModule(models.Model):

        JSON_FIELDS = ["variables"]
        """the fields that are stored as JSON dumps"""

        name = models.TextField(blank=True, default='')
        """the name of the check module"""

        description = models.TextField(blank=True, default='')
        """the description of the check module"""

        codes = models.TextField(blank=True, default='')
        """the codes of the check module"""
    
        variables = models.TextField(blank=True, default='[]')
        """ varaibles used in the check module defined in a similar way to variables in a PolicyTemplate"""

        def loads(self, attr):
            return json.loads(getattr(self, attr))

        def __str__(self):
            return self.name
        
        def to_json(self):
            return {
                "name": self.name,
                "codes": self.codes
            }

class FilterModule(models.Model):

    JSON_FIELDS = ["variables"]
    """the fields that are stored as JSON dumps"""

    kind = models.TextField(blank=True, default="")
    """The entity of the filter module e.g., CommunityUser, Text, or Channel """

    name = models.TextField(blank=True, default="")
    """the name of the filter module e.g., permission """

    description = models.TextField(blank=True, default="")
    """The description of the filter module e.g., users with a given permission """

    platform = models.TextField(choices=Procedure.PLATFORMS, blank=True, default=Procedure.ALL)
    """the platform this filter can apply to. It could be specific to one platform or all platforms"""

    variables = models.TextField(blank=True, default='[]')
    """
        variables needed in this filter module e.g., permission users are asked to specify
        But we will not create a policy variable for these variables 
        because we asume users may not change which governable actions a policy should be applied to 
        after the policy is created
    """

    codes = models.TextField(blank=True, default="")
    """
        how to generate codes for this filter module.
        It should be a block of codes that takes an object and variables as parameters and then 
        returns a boolean value indicating whether the object passes the filter, 
        as well as a list of filtered values (if the filter is checking whether the object is an element of a list) 
        We used a placeholder platform to represent the actual platform designated by the user when creating a policy

        For instance, a text.startswith filter should have codes like this: "return object.startswith(word), None"
        a communityUser.role filter should have codes like this：
            all_usernames_with_roles = [_user.username for _user in {platform}.get_users(role_names=[role])]\n
            return (object.username in all_usernames_with_roles) if object else None, all_usernames_with_roles\n
        
        This is to faciliate the use of filters in specifying a list of objects for a variable or a field (e.g., users who are admins)

        Finally, when generating codes, we will put these codes under a function named kind.name (Text_startsWith or CommunityUser_Role) and 
        pass in parameters "object" and all names defined in variables. 
        We will take care of the type of these variables before passing them to these functions
    """

    def loads(self, attr):
        return json.loads(getattr(self, attr))
    
    def to_json(self, variables_value=None):
        """ 
            parameters: 
                variables_value
                    {"role": "test" ....} 
        
        """
        variables = self.loads("variables")
        # we should expect there is a value for each variable. Otherwise we should throw an Exception
        if variables_value:
            for variable in variables:
                if variable["name"] in variables_value:
                    variable["value"] = variables_value[variable["name"]]
        return {
            "kind": self.kind,
            "name": self.name,
            "codes": self.codes,
            "variables": variables
        }

##### Pre-delete and post-delete signal receivers

@receiver(pre_delete, sender=Community)
def pre_delete_community(sender, instance, **kwargs):
    # Before deleting a Community, use non_polymorphic to delete all related CommunityPlatforms.
    # This is necessary to delete without hitting some db relation bug that comes up.
    CommunityPlatform.objects.non_polymorphic().filter(community=instance).delete()


@receiver(pre_delete, sender=CommunityPlatform)
def pre_delete_community_platform(sender, instance, **kwargs):
    # Before deleting a CommunityPlatform, use non_polymorphic to delete all related actions.
    # This is necessary to delete without hitting some db relation bug that comes up.
    GovernableAction.objects.non_polymorphic().filter(community=instance).delete()

@receiver(post_delete, sender=Community)
def post_delete_community(sender, instance, **kwargs):
    # After deleting a Community, delete it in Metagov too.
    if instance.metagov_slug:
        metagov.get_community(instance.metagov_slug).delete()

@receiver(post_delete, sender=CommunityPlatform)
def post_delete_community_platform(sender, instance, **kwargs):
    # After deleting a CommunityPlatform, delete the Metagov Plugin associated with it (if any)
    try:
        plugin = instance.metagov_plugin
    except Exception:
        # Some CommunityPlatforms don't have associated metagov plugins, ignore
        return

    plugin.delete()
