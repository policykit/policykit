from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import Permission
from policyengine.models import (
    ActionType,
    Policy,
    CommunityUser,
    GovernableAction
)

class CustomAction(models.Model):
    
    '''
    Do we want to put the community variable here, recording which platform the resultant policy belongs to
    '''

    action_type = models.ForeignKey(ActionType, on_delete=models.CASCADE)
    """
        The action type that this filter applies to.
        1) ForeignKey: one filter only applies to one GovernableAction 
                    but users can create multiple filters for each GovernableAction
        2) CASCASE: when the action type is deleted (though unlikely to happen), 
                    then the filters applied to this type of action should also be deleted
    """

    filter = models.TextField(blank=True, default='')
    """
        e.g., filter = def(self, action):\nreturn action.text.startswith("vote")

        The filter code of the policy. 
        1) Compared to the filter in the Policy class, 
            this filter is generated from front-end by us and therefore we can make it more structured;
        2) blank: we allow it to be blank and in such cases, the filter will pass when the specified action type happens
    """

    policy = models.OneToOneField(Policy, on_delete=models.SET_NULL, blank=True, null=True)
    """
        The policy that this ActionFilter is used to create. 
        OneToOneField: one policy can only have one filter action
        SET_NULL: If the policy is deleted, we still want to keep some user custom ActionFilters
    """


    community_name = models.TextField(null=True, unique=True)
    """
        If users think this ActionFilter is frequently used, then they can name this filter 
            and we would show it in the CustomAction tab on the interface.
        
        When it is null it means that users do not think it is frequently used;
        We require it to be unique so that their permission codenames won't be the same
    """

    is_user_generated = models.BooleanField(default=False)
    """
        True if the user writes the filter code; False if we generate the code automatically. Default is False.
        If false, then we can recover the values from the filters in the following function.
    """
        
    
    def recover_specs(self):
        '''
        In the UI, we will first filter out all ActionFilter instances where the filter_name is not blank and 
            then show them in the CustomAction tab; 
        Therefore, we should also be able to recover from the filter function the specified values for this action type
        '''
        pass

    def generate_filter(self, specs):
        '''
        help generate the filters based on the specifications users make in the frontend
        '''
        pass
    
    @property
    def permissions(self):
        if self.community_name:
            # If it is a user custom action, it has a new permission name
            permissions = ((f"can_execute_{self.community_name}", "Can execute {self.community_name}"))
        else:
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

    policy = models.OneToOneField(Policy, on_delete=models.CASCADE, null=True)
    """
        The policy that this Procedure is used to create.
        OneToOneField: one policy can only have one procedure
        CASCADE: If the policy is deleted, we do not want to keep the procedures
    """

    class Meta:
        abstract = True
    
    def generate_codes(self):
        '''
            Generated codes for intialize, check, notify, success, and fail based on procedure variables defined in each subclass
        '''
        raise NotImplementedError

class EmptyProcedure(Procedure):
    '''
    for if-then trigger policies, the procedures should be an empty one
    '''
    def generate_codes(self):
        return {
            "initialize": "pass",
            "check": "return PASSED",
            "notify": "pass"
        }

class VotingProcedure(Procedure):

    BOOLEAN = "boolean",
    CHOICE = "choice"
    PollType = [(BOOLEAN, 'boolean'), (CHOICE, 'choice')]
        
    users = models.ManyToManyField(CommunityUser, verbose_name="Who should be eligible to vote", help_text='''Who should be eligible to vote''')    

    poll_type = models.CharField(choices=PollType, default=BOOLEAN, verbose_name="The type of the poll: a yes-no vote or choice vote", help_text="Choose the type of the poll: a yes-no vote or choice vote")

    duration = models.IntegerField(
                    null=True, default=None, 
                    verbose_name="when the vote is closed (in minutes)", 
                    help_text='''when the vote is closed (in minutes); 
                            a null value represents that the vote is closed 
                            as long as the success or failure is reached'''
                )
    
   
    minimum_yes_required = models.IntegerField(
                                null=False, default=1, 
                                verbose_name="How many number of yes votes are required to reach success", 
                                help_text="Decide how many number of yes votes are required to reach success"
                            )

    maximum_no_allowed = models.IntegerField(
                            null=False, default=1, 
                            verbose_name="How many number of no votes are allowed before we call a failure", 
                            help_text="Decice how many number of no votes are allowed before we call a failure"
                        )
       
    vote_message = models.TextField(null=False, default="Start a vote", 
                        verbose_name="Message to be posted in the channel when the vote starts",
                        help_text="What messages you would like to post in the channel when the vote starts"    
                    )

    def generate_codes(self):
        codes = dict()
        if self.poll_type == VotingProcedure.BOOLEAN: 
            codes["check"] = f'if not proposal.vote_post_id:\n  return None\n\nif {self.duration} > 0:\n  time_elapsed = proposal.get_time_elapsed()\n  if time_elapsed < datetime.timedelta(minutes={self.duration}):\n    return None\n\nyes_votes = proposal.get_yes_votes(users={self.users}).count()\nno_votes = proposal.get_no_votes(users={self.users}).count()\nlogger.debug(yes_votes + \" for,\" + no_votes + \" against.\")\nif yes_votes >= {self.minimum_yes_required}:\n  return PASSED\nelif no_votes >= {self.maximum_no_allowed}:\n  return FAILED\n\nreturn PROPOSED'
        elif self.poll_type == VotingProcedure.CHOICE:
            #TODO need to think about the voting mechanism of choice votes
            codes["check"] = "return PASSED\n"
        return codes

class PermissionProcedure(Procedure):

    required_perm = models.TextField(null=False, verbose_name="Required permission to perform this kind of action",
                        help_text="Which permission is need to perform this kind of action"    
                )

    def generate_codes(self):
        return {
            "check": f"if action.initiator.has_perm({self.required_perm}):\n  return PASSED\nelse:\n  return FAILED"
        }
    
class Execution(models.Model):

    action_type = models.ForeignKey(ActionType, on_delete=models.CASCADE)
    
    action = models.ForeignKey(GovernableAction, on_delete=models.SET_NULL)

    policy = models.ForeignKey(Policy, on_delete=models.SET_NULL, null=False)
    """
        The policy that this ActionFilter is used to create. 
        ForeignKey: one policy can have many executions
        SET_NULL: If the policy is deleted, we still want to keep the user-authored polices, and therefore the execution
    """

    def generate_codes(self):
        # each Governable Action implement a method that returns the execution codes.
        # currently only supports SlackPostMessage
        if hasattr(self.action, "execution_codes"):
            return {
                "execute": f"return {self.action.execution_codes()}"
            }


class PolicyFactory():

    def create_policy(kind, filter: CustomAction, procedure: Procedure, success: Execution, fail: Execution):
        pass