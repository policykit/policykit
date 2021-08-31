import logging

from django.contrib.auth.models import Permission
from django.db import models
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

from policyengine.models import (
    CommunityDoc,
    CommunityPlatform,
    CommunityRole,
    CommunityUser,
    PlatformAction,
    Policy,
    ActionType,
)


class ConstitutionCommunity(CommunityPlatform):
    """
    CommunityPlatform for the PolicyKit platform. All constitution actions are tied to this CommunityPlatform.
    """

    platform = "constitution"


class PolicykitAddCommunityDoc(PlatformAction):
    name = models.TextField()
    text = models.TextField()

    def __str__(self):
        return "Add Document: " + self.name

    def execute(self):
        CommunityDoc.objects.create(name=self.name, text=self.text, community=self.community.community)

    class Meta:
        permissions = (("can_execute_policykitaddcommunitydoc", "Can execute policykit add community doc"),)


class PolicykitChangeCommunityDoc(PlatformAction):
    doc = models.ForeignKey(CommunityDoc, models.SET_NULL, null=True)
    name = models.TextField()
    text = models.TextField()

    def __str__(self):
        return "Edit Document: " + self.name

    def execute(self):
        self.doc.name = self.name
        self.doc.text = self.text
        self.doc.save()

    class Meta:
        permissions = (("can_execute_policykitchangecommunitydoc", "Can execute policykit change community doc"),)


class PolicykitDeleteCommunityDoc(PlatformAction):
    doc = models.ForeignKey(CommunityDoc, models.SET_NULL, null=True)

    def __str__(self):
        if self.doc:
            return "Delete Document: " + self.doc.name
        return "Delete Document: [ERROR: doc not found]"

    def execute(self):
        self.doc.is_active = False
        self.doc.save()

    class Meta:
        permissions = (("can_execute_policykitdeletecommunitydoc", "Can execute policykit delete community doc"),)


class PolicykitRecoverCommunityDoc(PlatformAction):
    doc = models.ForeignKey(CommunityDoc, models.SET_NULL, null=True)

    def __str__(self):
        if self.doc:
            return "Recover Document: " + self.doc.name
        return "Recover Document: [ERROR: doc not found]"

    def execute(self):
        self.doc.is_active = True
        self.doc.save()

    class Meta:
        permissions = (("can_execute_policykitrecovercommunitydoc", "Can execute policykit recover community doc"),)


class PolicykitAddRole(PlatformAction):
    name = models.CharField("name", max_length=300)
    description = models.TextField(null=True, blank=True, default="")
    permissions = models.ManyToManyField(Permission)

    def __str__(self):
        return "Add Role: " + self.name

    def execute(self):
        role = CommunityRole.objects.create(
            role_name=self.name, description=self.description, community=self.community.community
        )
        for p in self.permissions.all():
            role.permissions.add(p)
        role.save()

    class Meta:
        permissions = (("can_execute_policykitaddrole", "Can execute policykit add role"),)


class PolicykitDeleteRole(PlatformAction):
    role = models.ForeignKey(CommunityRole, models.SET_NULL, null=True)

    def __str__(self):
        if self.role:
            return "Delete Role: " + self.role.role_name
        else:
            return "Delete Role: [ERROR: role not found]"

    def execute(self):
        try:
            self.role.delete()
        except AssertionError:  # Triggers if object has already been deleted
            pass

    class Meta:
        permissions = (("can_execute_policykitdeleterole", "Can execute policykit delete role"),)


class PolicykitEditRole(PlatformAction):
    role = models.ForeignKey(CommunityRole, models.SET_NULL, null=True)
    name = models.CharField("name", max_length=300)
    description = models.TextField(null=True, blank=True, default="")
    permissions = models.ManyToManyField(Permission)

    def __str__(self):
        return "Edit Role: " + self.name

    def execute(self):
        self.role.role_name = self.name
        self.role.description = self.description
        self.role.permissions.clear()
        for p in self.permissions.all():
            self.role.permissions.add(p)
        self.role.save()

    class Meta:
        permissions = (("can_execute_policykiteditrole", "Can execute policykit edit role"),)


class PolicykitAddUserRole(PlatformAction):
    role = models.ForeignKey(CommunityRole, models.CASCADE)
    users = models.ManyToManyField(CommunityUser)

    def __str__(self):
        first_user = self.users.first()
        if self.role and first_user:
            return "Add User: " + str(first_user) + " to Role: " + self.role.role_name
        elif first_user is None:
            return f"Add User: [ERROR: no users] to role {self.role.role_name}"
        else:
            return "Add User to Role: [ERROR: role not found]"

    def execute(self):
        for u in self.users.all():
            self.role.user_set.add(u)

    class Meta:
        permissions = (("can_execute_policykitadduserrole", "Can execute policykit add user role"),)


class PolicykitRemoveUserRole(PlatformAction):
    role = models.ForeignKey(CommunityRole, models.CASCADE)
    users = models.ManyToManyField(CommunityUser)

    def __str__(self):
        if self.role:
            return "Remove User: " + str(self.users.all()[0]) + " from Role: " + self.role.role_name
        else:
            return "Remove User from Role: [ERROR: role not found]"

    def execute(self):
        for u in self.users.all():
            self.role.user_set.remove(u)

    class Meta:
        permissions = (("can_execute_policykitremoveuserrole", "Can execute policykit remove user role"),)


# Default values for code fields in editor
DEFAULT_FILTER = "return True\n\n"
DEFAULT_INITIALIZE = "pass\n\n"
DEFAULT_CHECK = "return PASSED\n\n"
DEFAULT_NOTIFY = "pass\n\n"
DEFAULT_SUCCESS = "action.execute()\n\n"
DEFAULT_FAIL = "pass\n\n"


class EditorModel(PlatformAction):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)

    action_types = models.ManyToManyField(ActionType)

    filter = models.TextField(blank=True, default=DEFAULT_FILTER, verbose_name="Filter")
    initialize = models.TextField(blank=True, default=DEFAULT_INITIALIZE, verbose_name="Initialize")
    check = models.TextField(blank=True, default=DEFAULT_CHECK, verbose_name="Check")
    notify = models.TextField(blank=True, default=DEFAULT_NOTIFY, verbose_name="Notify")
    success = models.TextField(blank=True, default=DEFAULT_SUCCESS, verbose_name="Pass")
    fail = models.TextField(blank=True, default=DEFAULT_FAIL, verbose_name="Fail")

    class Meta:
        abstract = True

    def save_to_policy(self, policy):
        """
        Apply the fields on this EditorModel to a Policy, and save it.
        """
        policy.community = self.community.community
        policy.name = self.name
        policy.description = self.description
        policy.filter = self.filter
        policy.initialize = self.initialize
        policy.check = self.check
        policy.notify = self.notify
        policy.success = self.success
        policy.fail = self.fail
        policy.save()
        policy.action_types.set(self.action_types.all())


class PolicykitAddPlatformPolicy(EditorModel):
    def __str__(self):
        return "Add Platform Policy: " + self.name

    def execute(self):
        policy = Policy(kind=Policy.PLATFORM)
        self.save_to_policy(policy)

    class Meta:
        permissions = (("can_execute_addpolicykitplatformpolicy", "Can execute policykit add platform policy"),)


class PolicykitAddConstitutionPolicy(EditorModel):
    def __str__(self):
        return "Add Constitution Policy: " + self.name

    def execute(self):
        policy = Policy(kind=Policy.CONSTITUTION)
        self.save_to_policy(policy)

    class Meta:
        permissions = (
            ("can_execute_policykitaddconstitutionpolicy", "Can execute policykit add constitution policy"),
        )


class PolicykitChangePlatformPolicy(EditorModel):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        return "Change Platform Policy: " + self.name

    def execute(self):
        assert self.policy.kind == Policy.PLATFORM
        self.save_to_policy(self.policy)

    class Meta:
        permissions = (("can_execute_policykitchangeplatformpolicy", "Can execute policykit change platform policy"),)


class PolicykitChangeConstitutionPolicy(EditorModel):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        return "Change Constitution Policy: " + self.name

    def execute(self):
        assert self.policy.kind == Policy.CONSTITUTION
        self.save_to_policy(self.policy)

    class Meta:
        permissions = (
            ("can_execute_policykitchangeconstitutionpolicy", "Can execute policykit change constitution policy"),
        )


class PolicykitRemovePlatformPolicy(PlatformAction):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        if self.platform_policy:
            return "Remove Platform Policy: " + self.platform_policy.name
        return "Remove Platform Policy: [ERROR: platform policy not found]"

    def execute(self):
        assert self.policy.kind == Policy.PLATFORM
        self.policy.is_active = False
        self.policy.save()

    class Meta:
        permissions = (("can_execute_policykitremoveplatformpolicy", "Can execute policykit remove platform policy"),)


class PolicykitRecoverPlatformPolicy(PlatformAction):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        if self.policy:
            return "Recover Platform Policy: " + self.policy.name
        return "Recover Platform Policy: [ERROR: platform policy not found]"

    def execute(self):
        assert self.policy.kind == Policy.PLATFORM
        self.policy.is_active = True
        self.policy.save()

    class Meta:
        permissions = (
            ("can_execute_policykitrecoverplatformpolicy", "Can execute policykit recover platform policy"),
        )


class PolicykitRemoveConstitutionPolicy(PlatformAction):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        if self.policy:
            return "Remove Constitution Policy: " + self.policy.name
        return "Remove Constitution Policy: [ERROR: constitution policy not found]"

    def execute(self):
        assert self.policy.kind == Policy.CONSTITUTION
        self.policy.is_active = False
        self.policy.save()

    class Meta:
        permissions = (
            ("can_execute_policykitremoveconstitutionpolicy", "Can execute policykit remove constitution policy"),
        )


class PolicykitRecoverConstitutionPolicy(PlatformAction):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        if self.policy:
            return "Recover Constitution Policy: " + self.policy.name
        return "Recover Constitution Policy: [ERROR: constitution policy not found]"

    def execute(self):
        assert self.policy.kind == Policy.CONSTITUTION
        self.policy.is_active = True
        self.policy.save()

    class Meta:
        permissions = (
            ("can_execute_policykitrecoverconstitutionpolicy", "Can execute policykit recover constitution policy"),
        )
