from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.govinterface.models import LogEntry
from polymorphic.models import PolymorphicModel
from django.core.exceptions import ValidationError
from policyengine.views import execute_community_action, check_policy_code, check_filter_code, initialize_code
import urllib
import json

import logging


logger = logging.getLogger(__name__)

def on_transaction_commit(func):
    def inner(*args, **kwargs):
        transaction.on_commit(lambda: func(*args, **kwargs))

    return inner

class CommunityIntegration(PolymorphicModel):
    community_name = models.CharField('team_name', 
                              max_length=1000)
    
    base_role = models.OneToOneField('CommunityRole',
                                     models.CASCADE)
    
    community_guidelines = models.OneToOneField('CommunityDoc',
                                     models.CASCADE)
    
    
    
    def notify_action(self, action, policy, users):
        pass
    
    def save(self, *args, **kwargs):   
        if not self.pk:
            super(CommunityIntegration, self).save(*args, **kwargs)
            
            # create Starter ProcessPolicy
            
            p = ProcessPolicy()
            p.community_integration = self
            p.policy_filter_code = "action_pass=True"
            p.policy_init_code = "pass"
            p.policy_notify_code = "pass"
            p.policy_conditional_code = "policy_pass = Proposal.PASSED"
            p.policy_action_code = "action.execute()"
            p.policy_failure_code = "pass"
            p.explanation = "Starter Policy: all policies pass"
            
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
            
            p11 = Permission.objects.get(name='Can add processactionbundle')
            self.base_role.permissions.add(p11)
            p12 = Permission.objects.get(name='Can add processpolicybundle')
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
            p1 = Permission.objects.get(name='Can add policykit change process policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit remove community policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit remove process policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit add community policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit add process policy')
            self.base_role.permissions.add(p1)
            p1 = Permission.objects.get(name='Can add policykit change community doc')
            self.base_role.permissions.add(p1)
            

        else:
            super(CommunityIntegration, self).save(*args, **kwargs)


class CommunityRole(Group):
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE,
                                   null=True)

    class Meta:
        verbose_name = 'communityrole'
        verbose_name_plural = 'communityroles'

    def save(self, *args, **kwargs):
        super(CommunityRole, self).save(*args, **kwargs)
    

class CommunityUser(User, PolymorphicModel):
        
    readable_name = models.CharField('readable_name', 
                                      max_length=300, null=True)
    
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
    
        
    access_token = models.CharField('access_token', 
                                     max_length=300, null=True)
    
    is_community_admin = models.BooleanField(default=False)            
        
    def __str__(self):
        return self.readable_name + '@' + self.community_integration.community_name


class CommunityDoc(models.Model):
    
    text = models.TextField()
    
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
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
    proposal_time = models.DateTimeField(auto_now_add=True)
    call_type = models.CharField('call_type', max_length=300)
    extra_info = models.TextField()
    
    @classmethod
    def make_api_call(cls, community_integration, values, call):
        logger.info("COMMUNITY API CALL")
        logger.info(call)
             
        _ = LogAPICall.objects.create(community_integration = community_integration,
                                      call_type = call,
                                      extra_info = json.dumps(values)
                                      )
        
        data = urllib.parse.urlencode(values)   
        data = data.encode('utf-8')
        logger.info(data)
        
        call_info = call + '?'
        req = urllib.request.Request(call_info, data)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        logger.info("COMMUNITY API RESPONSE")
        logger.info(res)
        return res
    
        
class Proposal(models.Model):
    
    author = models.ForeignKey(
        CommunityUser,
        models.CASCADE,
        verbose_name='author', 
        blank=True,
        null=True
        )
    
    proposal_time = models.DateTimeField(auto_now_add=True)
    
    PROPOSED = 'proposed'
    FAILED = 'failed'
    PASSED = 'passed'
    
    STATUS = [
            (PROPOSED, 'proposed'),
            (FAILED, 'failed'),
            (PASSED, 'passed')
        ]
    
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
    community_integration = models.ForeignKey(CommunityIntegration, 
        models.CASCADE,
        verbose_name='community_integration',
    )
    
    community_post = models.CharField('community_post', 
                                         max_length=300, null=True)
    
    proposal = models.OneToOneField(Proposal,
                                 models.CASCADE)
    
    
    is_bundled = models.BooleanField(default=False)
    
    data = models.OneToOneField(DataStore, 
        models.CASCADE,
        verbose_name='data',
        null=True
    )
    
    class Meta:
        abstract = True   


class ProcessAction(BaseAction, PolymorphicModel):
    
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
    
    initiator = models.ForeignKey(CommunityUser,
                                models.CASCADE,
                                null=True)
    
    is_bundled = models.BooleanField(default=False)
    

    action_type = "ProcessAction"
    
    class Meta:
        verbose_name = 'processaction'
        verbose_name_plural = 'processactions'
        
        
    def pass_action(self):
        proposal = self.proposal
        proposal.status = Proposal.PASSED
        proposal.save()

        
    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            p = Proposal.objects.create(status=Proposal.PROPOSED,
                                            author=self.initiator)
            self.proposal = p
            super(ProcessAction, self).save(*args, **kwargs)
            
            if not self.is_bundled:
                action = self
                for policy in ProcessPolicy.objects.filter(community_integration=self.community_integration):
                    if check_filter_code(policy, action):
                        
                        initialize_code(policy, action)
                        
                        cond_result = check_policy_code(policy, action)
                        if cond_result == Proposal.PASSED:
                            exec(policy.policy_action_code)
                        elif cond_result == Proposal.FAILED:
                            exec(policy.policy_failure_code)
                        else:
                            exec(policy.policy_notify_code)
        else:
            super(ProcessAction, self).save(*args, **kwargs)


class ProcessActionBundle(BaseAction):
      
    bundled_actions = models.ManyToManyField(ProcessAction)
    
    action_type = "ProcessActionBundle"
    
    ELECTION = 'election'
    BUNDLE = 'bundle'
    
    BUNDLE_TYPE = [
            (ELECTION, 'election'),
            (BUNDLE, 'bundle')
        ]
    
    bundle_type = models.CharField(choices=BUNDLE_TYPE, max_length=10)

    def execute(self):
        if self.bundle_type == ProcessActionBundle.BUNDLE:
            for action in self.bundled_actions.all():
                action.execute()
                action.pass_action()
                
    def pass_action(self):
        proposal = self.proposal
        proposal.status = Proposal.PASSED
        proposal.save()

    class Meta:
        verbose_name = 'processactionbundle'
        verbose_name_plural = 'processactionbundles'


@receiver(post_save, sender=ProcessActionBundle)
@on_transaction_commit
def after_processaction_bundle_save(sender, instance, **kwargs):
    action = instance

    for policy in ProcessPolicy.objects.filter(community_integration=action.community_integration):
        if check_filter_code(policy, action):
            
            initialize_code(policy, action)
            
            cond_result = check_policy_code(policy, action)
            if cond_result == Proposal.PASSED:
                exec(policy.policy_action_code)
            elif cond_result == Proposal.FAILED:
                exec(policy.policy_failure_code)
            else:
                exec(policy.policy_notify_code)



class PolicykitChangeCommunityDoc(ProcessAction):
    change_text = models.TextField()
    
    def execute(self):        
        self.community_integration.community_guidelines.change_text(self.change_text)
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit change community doc'),
        )



class PolicykitAddRole(ProcessAction):
    
    name = models.CharField('name', max_length=300)

    permissions = models.ManyToManyField(Permission)
    
    
    def __str__(self):
        perms = ""
        return "Add Role -  name: " + self.name + ", permissions: " 


    def execute(self):
        g,_ = CommunityRole.objects.get_or_create(name=self.name + '_' + self.community_integration.community_name)
        
        for p in self.permissions.all():
            g.permissions.add(p)   
            
        self.pass_action()
    
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit add role'),
        )


class PolicykitDeleteRole(ProcessAction):
    role = models.ForeignKey(CommunityRole,
                             models.SET_NULL,
                             null=True)
    
    def execute(self):        
        self.role.delete()
        self.pass_action()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit delete role'),
        )


class PolicykitAddPermission(ProcessAction):
    role = models.ForeignKey(CommunityRole,
                             models.CASCADE)
    
    permissions = models.ManyToManyField(Permission)
    
    def execute(self):        
        for p in self.permissions.all():
            self.role.permissions.add(p)  
        
        self.pass_action()
        
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit add permission'),
        )


class PolicykitRemovePermission(ProcessAction):
    role = models.ForeignKey(CommunityRole,
                             models.CASCADE)
    
    permissions = models.ManyToManyField(Permission)
    
    def execute(self):        
        for p in self.permissions.all():
            self.role.permissions.remove(p) 
        
        self.pass_action() 
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit remove permission'),
        )


class PolicykitAddUserRole(ProcessAction):
    role = models.ForeignKey(CommunityRole,
                             models.CASCADE)
    
    users = models.ManyToManyField(CommunityUser)
    
    def execute(self):        
        for u in self.users.all():
            self.role.user_set.add(u)
        
        self.pass_action()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit add user role'),
        )


class PolicykitRemoveUserRole(ProcessAction):
    role = models.ForeignKey(CommunityRole,
                             models.CASCADE)
    
    users = models.ManyToManyField(CommunityUser)
    
    def execute(self):        
        for u in self.users.all():
            self.role.user_set.remove(u)  
        
        self.pass_action()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit remove user role'),
        )
        
class PolicykitAddCommunityPolicy(ProcessAction):    
    policy_filter_code = models.TextField(blank=True, default='')
    policy_init_code = models.TextField(blank=True, default='')
    policy_notify_code = models.TextField(blank=True, default='')
    policy_conditional_code = models.TextField(blank=True, default='')
    policy_action_code = models.TextField(blank=True, default='')
    policy_failure_code = models.TextField(blank=True, default='')
    
    policy_text = models.TextField(null=True, blank=True)
    
    explanation = models.TextField(null=True, blank=True)
    
    def execute(self):
        policy = CommunityPolicy()
        policy.policy_filter_code = self.policy_filter_code
        policy.policy_init_code = self.policy_init_code
        policy.policy_notify_code = self.policy_notify_code
        policy.policy_conditional_code = self.policy_conditional_code
        policy.policy_action_code = self.policy_action_code
        policy.policy_failure_code = self.policy_failure_code
        policy.policy_text = self.policy_text
        policy.explanation = self.explanation
        policy.is_bundled = self.is_bundled
        policy.community_integration = self.community_integration
        policy.save()
        
        self.pass_action()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit add community policy'),
        )


class PolicykitAddProcessPolicy(ProcessAction):    
    policy_filter_code = models.TextField(blank=True, default='')
    policy_init_code = models.TextField(blank=True, default='')
    policy_notify_code = models.TextField(blank=True, default='')
    policy_conditional_code = models.TextField(blank=True, default='')
    policy_action_code = models.TextField(blank=True, default='')
    policy_failure_code = models.TextField(blank=True, default='')
    
    policy_text = models.TextField(null=True, blank=True)
    
    explanation = models.TextField(null=True, blank=True)
    
    def execute(self):
        policy = ProcessPolicy()
        policy.policy_filter_code = self.policy_filter_code
        policy.policy_init_code = self.policy_init_code
        policy.policy_notify_code = self.policy_notify_code
        policy.policy_conditional_code = self.policy_conditional_code
        policy.policy_action_code = self.policy_action_code
        policy.policy_failure_code = self.policy_failure_code
        policy.policy_text = self.policy_text
        policy.explanation = self.explanation
        policy.is_bundled = self.is_bundled
        policy.community_integration = self.community_integration
        policy.save()
        
        self.pass_action()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit add process policy'),
        )
       
        
class PolicykitChangeCommunityPolicy(ProcessAction):
    community_policy = models.ForeignKey('CommunityPolicy',
                                         models.CASCADE)
    
    policy_filter_code = models.TextField(blank=True, default='')
    policy_init_code = models.TextField(blank=True, default='')
    policy_notify_code = models.TextField(blank=True, default='')
    policy_conditional_code = models.TextField(blank=True, default='')
    policy_action_code = models.TextField(blank=True, default='')
    policy_failure_code = models.TextField(blank=True, default='')
    
    policy_text = models.TextField(null=True, blank=True)
    
    explanation = models.TextField(null=True, blank=True)
    
    def execute(self):
        self.community_policy.policy_filter_code = self.policy_filter_code
        self.community_policy.policy_init_code = self.policy_init_code
        self.community_policy.policy_notify_code = self.policy_notify_code
        self.community_policy.policy_conditional_code = self.policy_conditional_code
        self.community_policy.policy_action_code = self.policy_action_code
        self.community_policy.policy_failure_code = self.policy_failure_code
        self.community_policy.policy_text = self.policy_text
        self.community_policy.explanation = self.explanation
        
        self.community_policy.save()
        
        self.pass_action()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit change community policy'),
        )
        
        
class PolicykitChangeProcessPolicy(ProcessAction):
    process_policy = models.ForeignKey('ProcessPolicy',
                                         models.CASCADE)
    
    policy_filter_code = models.TextField(blank=True, default='')
    policy_init_code = models.TextField(blank=True, default='')
    policy_notify_code = models.TextField(blank=True, default='')
    policy_conditional_code = models.TextField(blank=True, default='')
    policy_action_code = models.TextField(blank=True, default='')
    policy_failure_code = models.TextField(blank=True, default='')
    
    policy_text = models.TextField(null=True, blank=True)
    
    explanation = models.TextField(null=True, blank=True)
    
    def execute(self):
        self.process_policy.policy_filter_code = self.policy_filter_code
        self.process_policy.policy_init_code = self.policy_init_code
        self.process_policy.policy_notify_code = self.policy_notify_code
        self.process_policy.policy_conditional_code = self.policy_conditional_code
        self.process_policy.policy_action_code = self.policy_action_code
        self.process_policy.policy_failure_code = self.policy_failure_code
        self.process_policy.policy_text = self.policy_text
        self.process_policy.explanation = self.explanation
        self.process_policy.save()
        
        self.pass_action()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit change process policy'),
        )


class PolicykitRemoveCommunityPolicy(ProcessAction):
    community_policy = models.ForeignKey('CommunityPolicy',
                                         models.SET_NULL,
                                         null=True)
    
    def execute(self):        
        self.community_policy.delete()
        
        self.pass_action()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit remove community policy'),
        )
        

class PolicykitRemoveProcessPolicy(ProcessAction):
    process_policy = models.ForeignKey('ProcessPolicy',
                                         models.SET_NULL,
                                         null=True)
    
    def execute(self):        
        self.process_policy.delete()
        
        self.pass_action()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit remove process policy'),
        )




class CommunityAction(BaseAction,PolymorphicModel):
    ACTION = None
    AUTH = 'app'
    
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
    
    initiator = models.ForeignKey(CommunityUser,
                                models.CASCADE)
    
    community_revert = models.BooleanField(default=False)
    
    community_origin = models.BooleanField(default=False)
    
    is_bundled = models.BooleanField(default=False)
    
    action_type = "CommunityAction"
    
    
    class Meta:
        verbose_name = 'communityaction'
        verbose_name_plural = 'communityactions'

    def revert(self, values, call):
        _ = LogAPICall.make_api_call(self.community_integration, values, call)
        self.community_revert = True
        self.save()

    def execute(self):
        execute_community_action(self)
        self.pass_action()
        
    def pass_action(self):
        proposal = self.proposal
        proposal.status = Proposal.PASSED
        proposal.save()
        

    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            
            p = Proposal.objects.create(status=Proposal.PROPOSED,
                                        author=self.initiator)
            
            self.proposal = p
            
            super(CommunityAction, self).save(*args, **kwargs)
            
            
            if not self.is_bundled:
                action = self
                for policy in CommunityPolicy.objects.filter(community_integration=self.community_integration):
                    if check_filter_code(policy, action):
                        
                        initialize_code(policy, action)
                        
                        cond_result = check_policy_code(policy, action)
                        if cond_result == Proposal.PASSED:
                            exec(policy.policy_action_code)
                        elif cond_result == Proposal.FAILED:
                            exec(policy.policy_failure_code)
                        else:
                            exec(policy.policy_notify_code)

        else:   
            super(CommunityAction, self).save(*args, **kwargs)
        

  
class CommunityActionBundle(BaseAction):
      
    bundled_actions = models.ManyToManyField(CommunityAction)
    
    action_type = "CommunityActionBundle"
    
    ELECTION = 'election'
    BUNDLE = 'bundle'
    
    BUNDLE_TYPE = [
            (ELECTION, 'election'),
            (BUNDLE, 'bundle')
        ]
    
    bundle_type = models.CharField(choices=BUNDLE_TYPE, max_length=10)

    def execute(self):
        if self.bundle_type == CommunityActionBundle.BUNDLE:
            for action in self.bundled_actions.all():
                execute_community_action(action)
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
    
    if not action.community_post:
        for policy in CommunityPolicy.objects.filter(community_integration=action.community_integration):
            if check_filter_code(policy, action):
                
                initialize_code(policy, action)
                
                cond_result = check_policy_code(policy, action)
                if cond_result == Proposal.PASSED:
                    exec(policy.policy_action_code)
                elif cond_result == Proposal.FAILED:
                    exec(policy.policy_failure_code)
                else:
                    exec(policy.policy_notify_code)
  
    

class BasePolicy(models.Model):
    community_integration = models.ForeignKey(CommunityIntegration, 
        models.CASCADE,
        verbose_name='community_integration',
    )
    
    explanation = models.TextField(null=True, blank=True)
    
    is_bundled = models.BooleanField(default=False)
    
    has_notified = models.BooleanField(default=False)
    
    data = models.OneToOneField(DataStore, 
        models.CASCADE,
        verbose_name='data',
        null=True
    )
    
    class Meta:
        abstract = True
    
    
class ProcessPolicy(BasePolicy):    
    policy_filter_code = models.TextField(blank=True, default='')
    policy_init_code = models.TextField(blank=True, default='')
    policy_notify_code = models.TextField(blank=True, default='')
    policy_conditional_code = models.TextField(blank=True, default='')
    policy_action_code = models.TextField(blank=True, default='')
    policy_failure_code = models.TextField(blank=True, default='')
    
    policy_text = models.TextField(null=True, blank=True)
    
    policy_type = "ProcessPolicy"
    
    class Meta:
        verbose_name = 'processpolicy'
        verbose_name_plural = 'processpolicies'

        
    def __str__(self):
        return ' '.join(['ProcessPolicy: ', self.explanation, 'for', self.community_integration.community_name])

 
class ProcessPolicyBundle(BaseAction):
       
    bundled_policies = models.ManyToManyField(ProcessPolicy)
     
    explanation = models.TextField(blank=True, default='')
     
    policy_type = "ProcessPolicyBundle"
 
    class Meta:
        verbose_name = 'processpolicybundle'
        verbose_name_plural = 'processpolicybundles'
 
    
class CommunityPolicy(BasePolicy):
    policy_filter_code = models.TextField(blank=True, default='')
    policy_init_code = models.TextField(blank=True, default='')
    policy_notify_code = models.TextField(blank=True, default='')
    policy_conditional_code = models.TextField(blank=True, default='')
    policy_action_code = models.TextField(blank=True, default='')
    policy_failure_code = models.TextField(blank=True, default='')
    
    policy_text = models.TextField(null=True, blank=True)
    
    policy_type = "CommunityPolicy"
    
    class Meta:
        verbose_name = 'communitypolicy'
        verbose_name_plural = 'communitypolicies'
        
        
    def __str__(self):
        return ' '.join(['CommunityPolicy: ', self.explanation, 'for', self.community_integration.community_name])
   
   
class CommunityPolicyBundle(BaseAction):
      
    bundled_policies = models.ManyToManyField(CommunityPolicy)
    
    explanation = models.TextField(blank=True, default='')
    
    policy_type = "CommunityPolicyBundle"

    class Meta:
        verbose_name = 'communitypolicybundle'
        verbose_name_plural = 'communitypolicybundles'
  


class UserVote(models.Model):
    
    user = models.ForeignKey(CommunityUser,
                              models.CASCADE)
    
    proposal = models.ForeignKey(Proposal,
                                models.CASCADE)
    
    class Meta:
        abstract = True
     

class BooleanVote(UserVote):
    boolean_value = models.BooleanField() # yes/no, selected/not selected

class NumberVote(UserVote):
    number_value = models.IntegerField()








