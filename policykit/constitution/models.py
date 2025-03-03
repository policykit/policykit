import logging

from django.contrib.auth.models import Permission
from django.db import models

logger = logging.getLogger(__name__)

from policyengine.models import (
    CommunityDoc,
    CommunityPlatform,
    CommunityRole,
    CommunityUser,
    GovernableAction,
    Policy,
    ActionType,
    PolicyActionKind,
    PolicyVariable
)


class ConstitutionCommunity(CommunityPlatform):
    """
    CommunityPlatform for the PolicyKit platform. All constitution actions are tied to this CommunityPlatform.
    """

    platform = "constitution"


class ConstitutionAction(GovernableAction):
    kind = PolicyActionKind.CONSTITUTION

    class Meta:
        abstract = True


class PolicykitAddIntegration(models.Model):
    """
    Dummy model for permission to add integrations.
    TODO: make this into an executable/governable ConstitutionAction
    """

    class Meta:
        # No database table creation or deletion  \
        # operations will be performed for this model.
        managed = False

        # disable "add", "change", "delete"
        # and "view" default permissions
        default_permissions = ()

        permissions = [("can_add_integration", "Can add platform integration")]


class PolicykitRemoveIntegration(models.Model):
    """
    Dummy model for permission to add integrations.
    TODO: make this into an executable/governable ConstitutionAction
    """

    class Meta:
        # No database table creation or deletion  \
        # operations will be performed for this model.
        managed = False

        # disable "add", "change", "delete"
        # and "view" default permissions
        default_permissions = ()

        permissions = [("can_remove_integration", "Can remove platform integration")]


class PolicykitAddCommunityDoc(ConstitutionAction):
    name = models.TextField()
    text = models.TextField()
    ACTION_NAME = "Add Community Document"
    FILTER_PARAMETERS = [
        {
            "name": "name",
            "label": "Name",
            "entity": "Text",
            "prompt": "the name of the community document",
            "is_list": False,
            "type": "string",
        },
        {
            "name": "text",
            "label": "Document Content",
            "entity": "Text",
            "prompt": "the content of the community document",
            "is_list": False,
            "type": "string"
        }
    ]

    def __str__(self):
        return "Add Document: " + self.name

    def execute(self):
        CommunityDoc.objects.create(name=self.name, text=self.text, community=self.community.community)

    class Meta:
        permissions = (("can_execute_policykitaddcommunitydoc", "Can execute policykit add community doc"),)


class PolicykitChangeCommunityDoc(ConstitutionAction):
    doc = models.ForeignKey(CommunityDoc, models.SET_NULL, null=True)
    name = models.TextField()
    text = models.TextField()
    ACTION_NAME = "Edit Community Document"
    FILTER_PARAMETERS = [
        {
            "name": "name",
            "label": "Name",
            "entity": "Text",
            "prompt": "the name of the community document",
            "is_list": False,
            "type": "string",
        },
        {
            "name": "text",
            "label": "Document Content",
            "entity": "Text",
            "prompt": "the content of the community document",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "doc",
            "label": "Document",
            "entity": "CommunityDoc",
            "prompt": "the community document that is edited",
            "is_list": False,
            "type": "string"
        }
    ]
    def __str__(self):
        return "Edit Document: " + self.name

    def execute(self):
        self.doc.name = self.name
        self.doc.text = self.text
        self.doc.save()

    class Meta:
        permissions = (("can_execute_policykitchangecommunitydoc", "Can execute policykit change community doc"),)


class PolicykitDeleteCommunityDoc(ConstitutionAction):
    doc = models.ForeignKey(CommunityDoc, models.SET_NULL, null=True)
    ACTION_NAME = "Delete Community Document"
    FILTER_PARAMETERS = [
        {
            "name": "doc",
            "label": "Document",
            "entity": "CommunityDoc",
            "prompt": "the community document that is deleted",
            "is_list": False,
            "type": "string"
        }
    ]
    def __str__(self):
        if self.doc:
            return "Delete Document: " + self.doc.name
        return "Delete Document: [ERROR: doc not found]"

    def execute(self):
        self.doc.is_active = False
        self.doc.save()

    class Meta:
        permissions = (("can_execute_policykitdeletecommunitydoc", "Can execute policykit delete community doc"),)


class PolicykitRecoverCommunityDoc(ConstitutionAction):
    doc = models.ForeignKey(CommunityDoc, models.SET_NULL, null=True)

    # this action seems to be quite useless as a governable action
    def __str__(self):
        if self.doc:
            return "Recover Document: " + self.doc.name
        return "Recover Document: [ERROR: doc not found]"

    def execute(self):
        self.doc.is_active = True
        self.doc.save()

    class Meta:
        permissions = (("can_execute_policykitrecovercommunitydoc", "Can execute policykit recover community doc"),)


class PolicykitAddRole(ConstitutionAction):
    name = models.CharField("name", max_length=300)
    description = models.TextField(null=True, blank=True, default="")
    permissions = models.ManyToManyField(Permission)
    ACTION_NAME = "Create User Role"
    FILTER_PARAMETERS = [
        {
            "name": "name",
            "label": "Role Name",
            "entity": "Text",
            "prompt": "the name of the role",
            "is_list": False,
            "type": "string",
        },
        {
            "name": "permissions",
            "label": "Permissions",
            "entity": "Permission",
            "prompt": "the permissions of the role",
            "is_list": True,
            "type": "string"
        }
    ]
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


class PolicykitDeleteRole(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.SET_NULL, null=True)
    ACTION_NAME = "Delete User Role"
    FILTER_PARAMETERS = [
        {
            "name": "role",
            "label": "Role",
            "entity": "CommunityRole",
            "prompt": "the deleted role",
            "is_list": False,
            "type": "string"
        }
    ]
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


class PolicykitEditRole(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.SET_NULL, null=True)
    name = models.CharField("name", max_length=300)
    description = models.TextField(null=True, blank=True, default="")
    permissions = models.ManyToManyField(Permission)
    ACTION_NAME = "Edit User Role"
    FILTER_PARAMETERS = [
        {
            "name": "name",
            "label": "Role Name",
            "entity": "Text",
            "prompt": "the name of the role",
            "is_list": False,
            "type": "string",
        },
        {
            "name": "permissions",
            "label": "Permissions",
            "entity": "Permission",
            "prompt": "the permissions of the role",
            "is_list": True,
            "type": "string"
        },
        {
            "name": "role",
            "label": "Role",
            "entity": "CommunityRole",
            "prompt": "the role that is edited",
            "is_list": False,
            "type": "string"
        }
    ]
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


class PolicykitAddUserRole(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.SET_NULL, null=True)
    users = models.ManyToManyField(CommunityUser)
    ACTION_NAME = "Grant Role to User"
    FILTER_PARAMETERS = [
        {
            "name": "role",
            "label": "Role",
            "entity": "CommunityRole",
            "prompt": "the role that is granted to users",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "users",
            "label": "Users",
            "entity": "CommunityUser",
            "prompt": "the users that the role is granted to",
            "is_list": True,
            "type": "string"
        }
    ]
    EXECUTE_VARIABLES = [
        {
            "name": "user",
            "label": "User",
            "entity": "CommunityUser",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "role",
            "label": "Role",
            "entity": "CommunityRole",
            "default": "",
            "is_required": True,
            "prompt": "the role that is granted to the user",
            "is_list": False,
            "type": "string"
        }
    ]

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

    def execution_codes(**kwargs):
        role = kwargs.get("role", None)
        user = kwargs.get("user", None)
        platform = kwargs.get("platform", None)
        if role and user and platform:
            return f"{platform}.assign_role(user={user}, role={role})"
        else:
            return ""
        


class PolicykitRemoveUserRole(ConstitutionAction):
    role = models.ForeignKey(CommunityRole, models.SET_NULL, null=True)
    users = models.ManyToManyField(CommunityUser)
    ACTION_NAME = "Revoke Role from User"
    FILTER_PARAMETERS = [
        {
            "name": "role",
            "label": "Role",
            "entity": "CommunityRole",
            "prompt": "the role that is removed from users",
            "is_list": False,
            "type": "string"
        },
        {
            "name": "users",
            "label": "Users",
            "entity": "CommunityUser",
            "prompt": "the users that the role is removed from",
            "is_list": True,
            "type": "string"
        }
    ]
    EXECUTE_VARIABLES = [
        {
            "name": "user",
            "label": "User",
            "entity": "CommunityUser",
            "default": "",
            "is_required": True,
            "prompt": "",
            "type": "string",
            "is_list": False
        },
        {
            "name": "role",
            "label": "Role",
            "entity": "CommunityRole",
            "default": "",
            "is_required": True,
            "prompt": "the role that is removed from the user",
            "is_list": False,
            "type": "string"
        }
    ]

    def __str__(self):
        if self.role and self.users.all().count() > 0:
            return "Remove User: " + str(self.users.all()[0]) + " from Role: " + self.role.role_name
        else:
            return "Remove User from Role: [ERROR: role not found]"

    def execute(self):
        for u in self.users.all():
            self.role.user_set.remove(u)

    class Meta:
        permissions = (("can_execute_policykitremoveuserrole", "Can execute policykit remove user role"),)

    def execution_codes(**kwargs):
        role = kwargs.get("role", None)
        user = kwargs.get("user", None)
        platform = kwargs.get("platform", None)
        if role and user and platform:
            return f"{platform}.remove_role(user={user}, role={role})"
        else:
            return ""

class EditorModel(ConstitutionAction):
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    action_types = models.ManyToManyField(ActionType)
    variables = models.JSONField(null=True, blank=True)
    filter = models.TextField(blank=True, verbose_name="Filter")
    initialize = models.TextField(blank=True, verbose_name="Initialize")
    check = models.TextField(blank=True, verbose_name="Check")
    notify = models.TextField(blank=True, verbose_name="Notify")
    success = models.TextField(blank=True, verbose_name="Pass")
    fail = models.TextField(blank=True, verbose_name="Fail")

    class Meta:
        abstract = True

    def get_existing_policy_variables(self):
        if self.variables:
            vars = [PolicyVariable.objects.filter(pk=id).first() for id in self.variables.keys()]
            return [var for var in vars if var is not None]
        else:
            return []

    def parse_policy_variables(self, validate=True, save=False):
        existing_variables = self.get_existing_policy_variables()

        for variable in existing_variables:
            # update variable's value based on variables JSON data, which is keyed by id
            variable.value = self.variables[f"{variable.pk}"]

            if validate:
                variable.clean()

            if save:
                variable.save()

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
        self.parse_policy_variables(save=True)


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


class PolicykitAddTriggerPolicy(EditorModel):
    def __str__(self):
        return "Add Trigger Policy: " + self.name

    def execute(self):
        logger.debug("adding trigger policy....")
        policy = Policy(kind=Policy.TRIGGER)
        self.save_to_policy(policy)

    class Meta:
        permissions = (("can_execute_policykitaddtriggerpolicy", "Can execute policykit add trigger policy"),)


class PolicykitChangePlatformPolicy(EditorModel):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        return "Change Platform Policy: " + self.name

    def execute(self):
        assert self.policy.kind == Policy.PLATFORM, "Expected platform policy"
        self.save_to_policy(self.policy)

    class Meta:
        permissions = (("can_execute_policykitchangeplatformpolicy", "Can execute policykit change platform policy"),)


class PolicykitChangeConstitutionPolicy(EditorModel):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        return "Change Constitution Policy: " + self.name

    def execute(self):
        assert self.policy.kind == Policy.CONSTITUTION, "Expected constitution policy"
        self.save_to_policy(self.policy)

    class Meta:
        permissions = (
            ("can_execute_policykitchangeconstitutionpolicy", "Can execute policykit change constitution policy"),
        )


class PolicykitChangeTriggerPolicy(EditorModel):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        return "Change Trigger Policy: " + self.name

    def execute(self):
        assert self.policy.kind == Policy.TRIGGER, "Expected trigger policy"
        self.save_to_policy(self.policy)

    class Meta:
        permissions = (("can_execute_policykitchangetriggerpolicy", "Can execute policykit change trigger policy"),)


class PolicykitRemovePlatformPolicy(ConstitutionAction):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        if self.policy:
            return "Remove Platform Policy: " + self.policy.name
        return "Remove Platform Policy: [ERROR: platform policy not found]"

    def execute(self):
        assert self.policy.kind == Policy.PLATFORM, "Expected platform policy"
        self.policy.is_active = False
        self.policy.save()

    class Meta:
        permissions = (("can_execute_policykitremoveplatformpolicy", "Can execute policykit remove platform policy"),)


class PolicykitRemoveConstitutionPolicy(ConstitutionAction):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        if self.policy:
            return "Remove Constitution Policy: " + self.policy.name
        return "Remove Constitution Policy: [ERROR: constitution policy not found]"

    def execute(self):
        assert self.policy.kind == Policy.CONSTITUTION, "Expected constitution policy"
        self.policy.is_active = False
        self.policy.save()

    class Meta:
        permissions = (
            ("can_execute_policykitremoveconstitutionpolicy", "Can execute policykit remove constitution policy"),
        )


class PolicykitRemoveTriggerPolicy(ConstitutionAction):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        if self.policy:
            return "Remove Trigger Policy: " + self.policy.name
        return "Remove Trigger Policy: [ERROR: trigger policy not found]"

    def execute(self):
        assert self.policy.kind == Policy.TRIGGER, "Expected trigger policy"
        self.policy.is_active = False
        self.policy.save()

    class Meta:
        permissions = (("can_execute_policykitremovetriggerpolicy", "Can execute policykit remove trigger policy"),)


class PolicykitRecoverPlatformPolicy(ConstitutionAction):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        if self.policy:
            return "Recover Platform Policy: " + self.policy.name
        return "Recover Platform Policy: [ERROR: platform policy not found]"

    def execute(self):
        assert self.policy.kind == Policy.PLATFORM, "Expected platform policy"
        self.policy.is_active = True
        self.policy.save()

    class Meta:
        permissions = (
            ("can_execute_policykitrecoverplatformpolicy", "Can execute policykit recover platform policy"),
        )


class PolicykitRecoverConstitutionPolicy(ConstitutionAction):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        if self.policy:
            return "Recover Constitution Policy: " + self.policy.name
        return "Recover Constitution Policy: [ERROR: constitution policy not found]"

    def execute(self):
        assert self.policy.kind == Policy.CONSTITUTION, "Expected constitution policy"
        self.policy.is_active = True
        self.policy.save()

    class Meta:
        permissions = (
            ("can_execute_policykitrecoverconstitutionpolicy", "Can execute policykit recover constitution policy"),
        )


class PolicykitRecoverTriggerPolicy(ConstitutionAction):
    policy = models.ForeignKey(Policy, models.SET_NULL, null=True)

    def __str__(self):
        if self.policy:
            return "Recover Trigger Policy: " + self.policy.name
        return "Recover Trigger Policy: [ERROR: trigger policy not found]"

    def execute(self):
        assert self.policy.kind == Policy.TRIGGER, "Expected trigger policy"
        self.policy.is_active = True
        self.policy.save()

    class Meta:
        permissions = (("can_execute_policykitrecovertriggerpolicy", "Can execute policykit recover trigger policy"),)
