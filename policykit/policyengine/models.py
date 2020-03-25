from django.db import models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.govinterface.models import LogEntry
from polymorphic.models import PolymorphicModel
from django.core.exceptions import ValidationError
from policyengine.views import post_policy, execute_community_action, check_policy_code, check_filter_code, initialize_code
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
            
            p1 = Permission.objects.get(name='Can add processpolicy')
            p2 = Permission.objects.get(name='Can view processpolicy')
            self.base_role.permissions.add(p1)
            self.base_role.permissions.add(p2)
            
            p1 = Permission.objects.get(name='Can add communitypolicy')
            p2 = Permission.objects.get(name='Can view communitypolicy')
            self.base_role.permissions.add(p1)
            self.base_role.permissions.add(p2)
            
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
            

            p1 = Permission.objects.get(name='Can view communityrole')
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
    
    def get_item(self, key):
        obj = self._get_data_store()
        return obj.get(key, None)
    
    def add_or_update_item(self, key, value):
        obj = self._get_data_store()
        obj[key] = value
        self._set_data_store(obj)
        return True
    
    def delete_item(self, key):
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
        

class PolicykitAPI(PolymorphicModel):
    
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
    
    initiator = models.ForeignKey(CommunityUser,
                                models.CASCADE,
                                null=True)
    
    is_bundled = models.BooleanField(default=False)
    
    def save(self, *args, **kwargs):    
        if not self.pk:
            # Runs only when object is new
            super(PolicykitAPI, self).save(*args, **kwargs)

            p = Proposal.objects.create(status=Proposal.PROPOSED,
                                        author=self.initiator)
        else:
            super(PolicykitAPI, self).save(*args, **kwargs) 

            p = self.proposal

        _ = ProcessAction.objects.create(
                community_integration=self.community_integration,
                api_action=self,
                proposal=p,
                is_bundled=self.is_bundled
            )
        

class PolicykitAddRole(PolicykitAPI):
    
    name = models.CharField('name', max_length=300)

    permissions = models.ManyToManyField(Permission)

    def execute(self):
        g,_ = CommunityRole.objects.get_or_create(name=self.name + '_' + self.community_integration.community_name)
        
        for p in self.permissions.all():
            g.permissions.add(p)   
    
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit add role'),
        )


class PolicykitDeleteRole(PolicykitAPI):
    role = models.ForeignKey(CommunityRole,
                             models.SET_NULL,
                             null=True)
    
    def execute(self):        
        self.role.delete()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit delete role'),
        )


class PolicykitAddPermission(PolicykitAPI):
    role = models.ForeignKey(CommunityRole,
                             models.CASCADE)
    
    permissions = models.ManyToManyField(Permission)
    
    def execute(self):        
        for p in self.permissions.all():
            self.role.permissions.add(p)  
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit add permission'),
        )


class PolicykitRemovePermission(PolicykitAPI):
    role = models.ForeignKey(CommunityRole,
                             models.CASCADE)
    
    permissions = models.ManyToManyField(Permission)
    
    def execute(self):        
        for p in self.permissions.all():
            self.role.permissions.remove(p)  
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit remove permission'),
        )


class PolicykitAddUserRole(PolicykitAPI):
    role = models.ForeignKey(CommunityRole,
                             models.CASCADE)
    
    users = models.ManyToManyField(CommunityUser)
    
    def execute(self):        
        for u in self.users.all():
            self.role.user_set.add(u)  
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit add user role'),
        )


class PolicykitRemoveUserRole(PolicykitAPI):
    role = models.ForeignKey(CommunityRole,
                             models.CASCADE)
    
    users = models.ManyToManyField(CommunityUser)
    
    def execute(self):        
        for u in self.users.all():
            self.role.user_set.remove(u)  
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit remove user role'),
        )
        
class PolicykitChangeCommunityPolicy(PolicykitAPI):
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
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit change community policy'),
        )
        
        
class PolicykitChangeProcessPolicy(PolicykitAPI):
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
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit change process policy'),
        )


class PolicykitRemoveCommunityPolicy(PolicykitAPI):
    community_policy = models.ForeignKey('CommunityPolicy',
                                         models.SET_NULL,
                                         null=True)
    
    def execute(self):        
        self.community_policy.delete()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit remove community policy'),
        )
        

class PolicykitRemoveProcessPolicy(PolicykitAPI):
    process_policy = models.ForeignKey('ProcessPolicy',
                                         models.SET_NULL,
                                         null=True)
    
    def execute(self):        
        self.process_policy.delete()
        
    class Meta:
        permissions = (
            ('can_execute', 'Can execute policykit remove process policy'),
        )

  
class CommunityAPI(PolymorphicModel):
    ACTION = None
    AUTH = 'app'
    
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
    
    initiator = models.ForeignKey(CommunityUser,
                                models.CASCADE)
    
    community_revert = models.BooleanField(default=False)
    
    community_origin = models.BooleanField(default=False)
    
    is_bundled = models.BooleanField(default=False)
    
    
    def revert(self, values, call):
        _ = LogAPICall.make_api_call(self.community_integration, values, call)
        self.community_revert = True
        self.save()
        
            
    def save(self, *args, **kwargs):        
        if not self.pk:
            # Runs only when object is new
            super(CommunityAPI, self).save(*args, **kwargs)
            
            _ = CommunityAction.objects.create(community_integration=self.community_integration,
                                               api_action=self,
                                               is_bundled=self.is_bundled
                                              )
        else:
            super(CommunityAPI, self).save(*args, **kwargs) 
        
        
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
    
    data = models.OneToOneField(DataStore, 
        models.CASCADE,
        verbose_name='data',
        null=True
    )
    
    def save(self, *args, **kwargs):
        if not self.pk:
            ds = DataStore.objects.create()
            self.data = ds
            
        super(Proposal, self).save(*args, **kwargs)
            
        if self.status == self.PASSED:
            cpb = CommunityPolicyBundle.objects.filter(proposal=self)
            if cpb.exists():
                cpb = cpb[0]
                bundled_policies = cpb.bundled_policies.all()
                for policy in bundled_policies:
                    proposal = policy.proposal
                    proposal.status = self.PASSED
                    proposal.save()
        

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
    
    class Meta:
        abstract = True   

#     def save(self, *args, **kwargs):
#         logger.info(self.community_post)
#         
#         if not self.pk:
#             super(BaseAction, self).save(*args, **kwargs)
#             
#         else:
#             super(BaseAction, self).save(*args, **kwargs)      
#         



class ProcessAction(BaseAction):
     
    api_action = models.OneToOneField(PolicykitAPI,
                                      models.CASCADE,
                                      null=True)
    
    content_type = models.ForeignKey(
        ContentType,
        models.CASCADE,
        verbose_name='content type',
        null=True
    )
    object_id = models.PositiveIntegerField(null=True)
    
    content_object = GenericForeignKey('content_type', 'object_id')
    
    
    action_type = "ProcessAction"
    
    class Meta:
        verbose_name = 'processaction'
        verbose_name_plural = 'processactions'
        
        
    def execute(self):
        if self.api_action:
            self.api_action.execute()
        else:
            proposal = self.proposal
            proposal.status = Proposal.PASSED
            proposal.save()

        
    def save(self, *args, **kwargs):

        super(ProcessAction, self).save(*args, **kwargs)
        
        if not self.is_bundled:
            action = self
            for policy in ProcessPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=self.community_integration):
                if check_filter_code(policy, action):
                    
                    initialize_code(policy, action)
                    
                    cond_result = check_policy_code(policy, action)
                    if cond_result == Proposal.PASSED:
                        exec(policy.policy_action_code)
                    elif cond_result == Proposal.FAILED:
                        exec(policy.policy_failure_code)
                    else:
                        exec(policy.policy_notify_code)


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
                if action.api_action:
                    action.api_action.execute()
                else:
                    proposal = action.proposal
                    proposal.status = Proposal.PASSED
                    proposal.save()

    class Meta:
        verbose_name = 'processactionbundle'
        verbose_name_plural = 'processactionbundles'


@receiver(post_save, sender=ProcessActionBundle)
@on_transaction_commit
def after_processaction_bundle_save(sender, instance, **kwargs):
    action = instance

    for policy in ProcessPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=action.community_integration):
        if check_filter_code(policy, action):
            
            initialize_code(policy, action)
            
            cond_result = check_policy_code(policy, action)
            if cond_result == Proposal.PASSED:
                exec(policy.policy_action_code)
            elif cond_result == Proposal.FAILED:
                exec(policy.policy_failure_code)
            else:
                exec(policy.policy_notify_code)



class CommunityAction(BaseAction):
    
    api_action = models.OneToOneField(CommunityAPI,
                                      models.CASCADE)
    
    action_type = "CommunityAction"
    
    class Meta:
        verbose_name = 'communityaction'
        verbose_name_plural = 'communityactions'

    def __str__(self):
        return ' '.join(['Action: ', str(self.api_action), 'to', self.community_integration.community_name])


    def execute(self):
        execute_community_action(self)

    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            
            p = Proposal.objects.create(status=Proposal.PROPOSED,
                                        author=self.api_action.initiator)
            
            self.proposal = p
            
            super(CommunityAction, self).save(*args, **kwargs)
            
            
            if not self.is_bundled:
                action = self
                for policy in CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=self.community_integration):
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

    class Meta:
        verbose_name = 'communityactionbundle'
        verbose_name_plural = 'communityactionbundles'

#     def save(self, *args, **kwargs):
#         if not self.pk:
#             # Runs only when object is new
#             super(CommunityActionBundle, self).save(*args, **kwargs)
# 
#         else:   
#             super(CommunityActionBundle, self).save(*args, **kwargs)

@receiver(post_save, sender=CommunityActionBundle)
@on_transaction_commit
def after_bundle_save(sender, instance, **kwargs):
    action = instance
    
    if not action.community_post:
        for policy in CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=action.community_integration):
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
    
    proposal = models.OneToOneField(Proposal,
                                 models.CASCADE)
    
    explanation = models.TextField(null=True, blank=True)
    
    is_bundled = models.BooleanField(default=False)
    
    has_notified = models.BooleanField(default=False)
    
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
    
    def save(self, *args, **kwargs):
        if not self.pk:    
            
            p = ProcessPolicy.objects.all()
            
            if p.exists():
                
                super(ProcessPolicy, self).save(*args, **kwargs)

                ctype = ContentType.objects.get_for_model(self)
                
                _ = ProcessAction.objects.create(
                        community_integration=self.community_integration,
                        api_action=None,
                        content_type=ctype,
                        object_id=self.id,
                        is_bundled=self.is_bundled,
                        proposal=self.proposal
                    )
            else:
                super(ProcessPolicy, self).save(*args, **kwargs)

        else:   
            super(ProcessPolicy, self).save(*args, **kwargs)


 
class ProcessPolicyBundle(BaseAction):
       
    bundled_policies = models.ManyToManyField(ProcessPolicy)
     
    explanation = models.TextField(blank=True, default='')
     
    policy_type = "ProcessPolicyBundle"
 
    class Meta:
        verbose_name = 'processpolicybundle'
        verbose_name_plural = 'processpolicybundles'
 
#     def save(self, *args, **kwargs):
#         if not self.pk:
#             # Runs only when object is new
#             super(CommunityActionBundle, self).save(*args, **kwargs)
# 
#         else:   
#             super(CommunityActionBundle, self).save(*args, **kwargs)
 
@receiver(post_save, sender=ProcessPolicyBundle)
@on_transaction_commit
def after_process_bundle_save(sender, instance, **kwargs):
    policy = instance
    
    ctype = ContentType.objects.get_for_model(policy)
            
    _ = ProcessAction.objects.create(
            community_integration=policy.community_integration,
            api_action=None,
            content_type=ctype,
            object_id=policy.id,
            is_bundled=policy.is_bundled,
            proposal=policy.proposal
        )
  
  


    
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
        
#     def clean(self):
#         super().clean()
#         if self.policy_action_code is None and self.policy_text is None:
#             raise ValidationError('Code or text rule instructions are both None')
        
    def __str__(self):
        return ' '.join(['CommunityPolicy: ', self.explanation, 'for', self.community_integration.community_name])
    
    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            
            super(CommunityPolicy, self).save(*args, **kwargs)
            
            ctype = ContentType.objects.get_for_model(self)
            
            _ = ProcessAction.objects.create(
                    community_integration=self.community_integration,
                    api_action=None,
                    content_type=ctype,
                    object_id=self.id,
                    is_bundled=self.is_bundled,
                    proposal=self.proposal
                )

        else:   
            super(CommunityPolicy, self).save(*args, **kwargs)
   
   
class CommunityPolicyBundle(BaseAction):
      
    bundled_policies = models.ManyToManyField(CommunityPolicy)
    
    explanation = models.TextField(blank=True, default='')
    
    policy_type = "CommunityPolicyBundle"

    class Meta:
        verbose_name = 'communitypolicybundle'
        verbose_name_plural = 'communitypolicybundles'

#     def save(self, *args, **kwargs):
#         if not self.pk:
#             # Runs only when object is new
#             super(CommunityActionBundle, self).save(*args, **kwargs)
# 
#         else:   
#             super(CommunityActionBundle, self).save(*args, **kwargs)

@receiver(post_save, sender=CommunityPolicyBundle)
@on_transaction_commit
def after_policy_bundle_save(sender, instance, **kwargs):
        
    policy = instance
        
    ctype = ContentType.objects.get_for_model(policy)
            
    _ = ProcessAction.objects.create(
            community_integration=policy.community_integration,
            api_action=None,
            content_type=ctype,
            object_id=policy.id,
            is_bundled=policy.is_bundled,
            proposal=policy.proposal
        )
  


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








