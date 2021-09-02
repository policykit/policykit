from django.db import models
from actstream import action as actstream_action
from django.contrib.auth.models import UserManager, User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.forms import ModelForm
from django.conf import settings
from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from polymorphic.models import PolymorphicModel, PolymorphicManager
import integrations.metagov.api as MetagovAPI
from policyengine import engine
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger(__name__)

"""
INIT PROCESS FOR FIRST PLATFORM

 - user consent to install
    - Community created in MG
 - create corresponding Community in PK
    - ConstitutionCommunity created for constitutional stuff

 - create SlackCommunity
    - create SlackUsers (creates empty base_role)
    - special token for the installing user

 - user chooses StarterKit
     - create policies
     - create CommunityRoles (updates the existing base_role)
     - add Permissions to each CommunityRole
     - add users to roles (may depend on is_community_admin status)
     

INIT PROCESS FOR SECOND PLATFORM

 - user consent to install
    - Community slug passed to MG. Plugin enabled in MG.

 - create SlackCommunity
    - create SlackUsers (they all get added to the base_role on save)
    - save special token for the installing user on SlackUser
"""


class PolicyActionKind:
    PLATFORM = "platform" #governable
    CONSTITUTION = "constitution" #governable
    TRIGGER = "trigger" #trigger


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
        if settings.METAGOV_ENABLED and is_new and not self.metagov_slug:
            # If this is the first save, create a corresponding community in Metagov
            response = MetagovAPI.create_empty_metagov_community()
            self.metagov_slug = response["slug"]
            logger.debug(f"Created new Metagov community '{self.metagov_slug}' Saving slug in model.")

        super(Community, self).save(*args, **kwargs)

@receiver(pre_delete, sender=Community)
def pre_delete_community(sender, instance, **kwargs):
    CommunityPlatform.objects.non_polymorphic().filter(community=instance).delete()

@receiver(post_delete, sender=Community)
def post_delete_community(sender, instance, **kwargs):
    if instance.metagov_slug and settings.METAGOV_ENABLED:
        MetagovAPI.delete_community(instance.metagov_slug)


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

    def get_platform_policies(self):
        """
        Returns a QuerySet of all platform policies for this ``CommunityPlatform``.
        """
        return Policy.platform_policies.filter(community=self.community).order_by('-modified_at')

    def get_roles(self):
        """
        Returns a QuerySet of all roles in the community.
        """
        return CommunityRole.objects.filter(community=self.community)

    def get_users(self):
        """
        Returns a QuerySet of all users in the community on this platform.
        """
        return CommunityUser.objects.filter(community=self)


    def execute_platform_action(self):
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
        return self.groups.filter(name=name).exists()


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

        # If this user is an admin in the community, give them access to edit the Metagov config
        if self.is_community_admin and settings.METAGOV_ENABLED:
            from integrations.metagov.models import MetagovConfig
            role,created = CommunityRole.objects.get_or_create(community=community, role_name="Integration Admin")
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

    community_post = models.CharField(max_length=300, blank=True)
    """Identifier of the post that is being voted on, if any."""

    governance_process_url = models.URLField(max_length=100, blank=True)
    """Location of the Metagov GovernanceProcess that is being used to make a decision about this Proposal, if any."""

    governance_process_json = models.JSONField(null=True, blank=True)
    """Raw Metagov governance process data in JSON format."""

    def __str__(self):
        return f"Proposal {self.pk}: {self.action} : {self.policy or 'POLICY_DELETED'} ({self.status})"

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

    def pass_evaluation(self):
        """
        Sets the proposal to PASSED.

        :meta private:
        """
        self.status = Proposal.PASSED
        self.save()
        action = self.action
        actstream_action.send(action, verb='was passed', community_id=action.community.id, action_codename=action.action_type)

    def fail_evaluation(self):
        """
        Sets the proposal to FAILED.

        :meta private:
        """
        self.status = Proposal.FAILED
        self.save()
        action = self.action
        actstream_action.send(action, verb='was failed', community_id=action.community.id, action_codename=action.action_type)

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

    @property
    def action_type(self):
        """The type of action (such as 'slackpostmessage' or 'policykitaddcommunitydoc')."""
        return self._meta.model_name


class TriggerAction(BaseAction, PolymorphicModel):
    """Trigger Action
    
    subtypes:
    -TriggerEvent (event occurred on platform or PK)
        - Event name
    -PolicyKitEvent (engine-event, like something passed or failed ?)
        - PlatformAction type
        - PlatformAction proposal state? (FAILED/PASSED) ? (or do this in Filter block)

    -webhook (some event that is NOT KNOWN TO POLICYKIT before hand! aka metagov.event_name)
            we want to consider this an action_type, I think.

            action_types = ["slackpostmessage", "discordpostmessage"]
            action_types = ["policykitaddcommunitydoc"]
            action_types = ["schedule"]
                filter = 'action.hour = 8 and not action.is_weekend'
                filter = 'action.day_of_month = 15'
                filter = 'action.day_of_week = THURSDAY'
            action_types = ["metagovwebhook"]
            action_types = [Webhook(event_name="loomio.stance_cast")]
            action_types = [SlackPostMessage(channel=ABCD)]

    -Schedule (hourly, daily, weekly, monthly)
        - cadence: hourly|weekly|daily|monthly
        - hour:
        - day_of_week:
        - day_of_month:
    """
    kind = PolicyActionKind.TRIGGER

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        should_evaluate = True if not self.pk else False
        super(TriggerAction, self).save(*args, **kwargs)
        if should_evaluate:
            engine.evaluate_action(self)


class PlatformAction(BaseAction, PolymorphicModel):
    """
    PLATFORM ACTION can be executed and reverted, is "governable"

    Constitution actions are Platform actions
    """
    kind = PolicyActionKind.PLATFORM

    ACTION = None
    AUTH = 'app'
    

    community_revert = models.BooleanField(default=False)
    """True if the action has been reverted on the platform."""

    community_origin = models.BooleanField(default=False)
    """True if the action originated on the platform. False if the action originated in PolicyKit, either from a Policy or being proposed in the PolicyKit web interface."""

    def __str__(self):
        return self.action_type or super(PlatformAction, self).__str__()

    def save(self, *args, **kwargs):
        """
        Saves the platform action. If new, evaluates against current policies.

        :meta private:
        """
        evaluate_action = kwargs.pop("evaluate_action", None)
        should_evaluate = (not self.pk and evaluate_action != False) or evaluate_action
        if should_evaluate:
            # Runs if initiator has propose permission, OR if there is no initiator.
            can_propose_perm = f"{self._meta.app_label}.add_{self.action_type}"
            if not self.initiator or self.initiator.has_perm(can_propose_perm):
                super(PlatformAction, self).save(*args, **kwargs)
                engine.evaluate_action(self)

        super(PlatformAction, self).save(*args, **kwargs)

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


class PlatformActionBundle(PlatformAction):
    ELECTION = 'election'
    BUNDLE = 'bundle'
    BUNDLE_TYPE = [
        (ELECTION, 'election'),
        (BUNDLE, 'bundle')
    ]

    bundled_actions = models.ManyToManyField(PlatformAction, related_name="member_of_bundle")
    bundle_type = models.CharField(choices=BUNDLE_TYPE, max_length=10)

    def execute(self):
        if self.bundle_type == PlatformActionBundle.BUNDLE:
            for action in self.bundled_actions.all():
                self.community.execute_platform_action(action)

class PlatformPolicyManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(kind=Policy.PLATFORM)

class ConstitutionPolicyManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(kind=Policy.CONSTITUTION)

class ActionType(models.Model):
    """The action_type of a BaseAction"""

    codename = models.CharField(max_length=30, unique=True)

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

    community = models.ForeignKey(Community, models.CASCADE)
    """The community which the policy belongs to."""

    action_types = models.ManyToManyField(ActionType)
    """The action types that this policy applies to."""

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

    @property
    def is_bundled(self):
        """True if the policy is part of a bundle"""
        return self.member_of_bundle.count() > 0


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
            "is_bundled"
        ]

    def __init__(self, *args, **kwargs):
        super(PlatformActionForm, self).__init__(*args, **kwargs)
        self.label_suffix = ''
