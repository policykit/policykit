from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.govinterface.models import LogEntry
from polymorphic.models import PolymorphicModel
from django.core.exceptions import ValidationError
from policyengine.views import execute_action, check_policy_code, check_filter_code
import urllib
import json

import logging


logger = logging.getLogger(__name__)



class CommunityIntegration(PolymorphicModel):
    community_name = models.CharField('team_name', 
                              max_length=1000)
    
    user_group = models.ForeignKey(Group, models.CASCADE)


class CommunityUser(User, PolymorphicModel):
        
    readable_name = models.CharField('readable_name', 
                                      max_length=300, null=True)
    
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
    
        
    access_token = models.CharField('access_token', 
                                     max_length=300)
    
    is_community_admin = models.BooleanField(default=False)
    
        
    def save(self, *args, **kwargs):      
        super(User, self).save(*args, **kwargs)
        p1 = Permission.objects.get(name='Can add processpolicy')
        p2 = Permission.objects.get(name='Can add communitypolicy')
        self.user_permissions.add(p1)
        self.user_permissions.add(p2)
        
        p3 = Permission.objects.get(name='Can add user vote')
        p4 = Permission.objects.get(name='Can change user vote')
        p5 = Permission.objects.get(name='Can delete user vote')
        p6 = Permission.objects.get(name='Can view user vote')
        self.user_permissions.add(p3)
        self.user_permissions.add(p4)
        self.user_permissions.add(p5)
        self.user_permissions.add(p6)
        
    def __str__(self):
        return self.readable_name + '@' + self.community_integration.community_name
        
        
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
        
        
class CommunityAPI(PolymorphicModel):
    ACTION = None
    AUTH = 'app'
    
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
    
    initiator = models.ForeignKey(CommunityUser,
                                models.CASCADE)
    
    community_post = models.CharField('community_post', 
                                         max_length=300, null=True)
    
    community_revert = models.BooleanField(default=False)
    
    community_origin = models.BooleanField(default=False)
    
    def revert(self, values, call):
        _ = LogAPICall.make_api_call(self.community_integration, values, call)
        self.community_revert = True
        self.save()
        
    def post_policy(self, values, call):
        policy = CommunityPolicy.objects.filter(community_integration=self.community_integration,
                                                proposal__status=Proposal.PASSED)

        if policy.count() > 0:
            policy = policy[0]
            # need more descriptive message
            policy_message = "This action is governed by the following policy: " + policy.explanation + '. Vote with :thumbsup: or :thumbsdown: on this post.'
            values['text'] = policy_message
            res = LogAPICall.make_api_call(self.community_integration, values, call)
            self.community_post = res['ts']   
            self.save()      
            
    def save(self, *args, **kwargs):
        logger.info(self.community_post)
        
        if not self.pk:
            # Runs only when object is new
            super(CommunityAPI, self).save(*args, **kwargs)
            p = Proposal.objects.create(status=Proposal.PROPOSED, author=self.initiator)
            _ = CommunityAction.objects.create(community_integration=self.community_integration,
                                               proposal=p,
                                               api_action=self
                                              )

        else:
            super(CommunityAPI, self).save(*args, **kwargs) 
        
        
class Proposal(models.Model):
    
    author = models.ForeignKey(
        CommunityUser,
        models.CASCADE,
        verbose_name='author', 
        blank=True
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

       
class BaseAction(models.Model):
    community_integration = models.ForeignKey(CommunityIntegration, 
        models.CASCADE,
        verbose_name='community_integration',
    )
    
    proposal = models.OneToOneField(Proposal,
                                 models.CASCADE)
    
    class Meta:
        abstract = True   


class ProcessAction(BaseAction):
     
    content_type = models.ForeignKey(
        ContentType,
        models.CASCADE,
        verbose_name='content type',
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        verbose_name = 'processaction'
        verbose_name_plural = 'processactions'


class CommunityAction(BaseAction):
    
    api_action = models.OneToOneField(CommunityAPI,
                                      models.CASCADE)
    
    class Meta:
        verbose_name = 'communityaction'
        verbose_name_plural = 'communityactions'

    def __str__(self):
        return ' '.join(['Action: ', str(self.api_action), 'to', self.community_integration.community_name])

    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            self.proposal.status = Proposal.PROPOSED
            
            super(CommunityAction, self).save(*args, **kwargs)
            
            action = self
            for policy in CommunityPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=self.community_integration):
                if check_filter_code(policy, action):
                    cond_result = check_policy_code(policy, action)
                    if cond_result == Proposal.PASSED:
                        exec(policy.policy_action_code)
                    elif cond_result == Proposal.FAILED:
                        exec(policy.policy_failure_code)

        else:   
            super(CommunityAction, self).save(*args, **kwargs)
        

  
class CommunityActionBundle(BaseAction):
#      
#     bundled_api_actions = models.ManyToManyField(CommunityAPI, 
#                                      models.CASCADE, 
#                                      verbose_name="bundled_api_actions")

    class Meta:
        verbose_name = 'communityactionbundle'
        verbose_name_plural = 'communityactionbundles'
    
    

class BasePolicy(models.Model):
    community_integration = models.ForeignKey(CommunityIntegration, 
        models.CASCADE,
        verbose_name='community_integration',
    )
    
    proposal = models.OneToOneField(Proposal,
                                 models.CASCADE)
    
    explanation = models.TextField(null=True, blank=True)
   
    data_store = models.TextField()
    
    class Meta:
        abstract = True
    
    
class ProcessPolicy(BasePolicy):    
    policy_code = models.TextField()
    
    class Meta:
        verbose_name = 'processpolicy'
        verbose_name_plural = 'processpolicies'

        
    def __str__(self):
        return ' '.join(['ProcessPolicy: ', self.explanation, 'for', self.community_integration.community_name])
    
    
    
class CommunityPolicy(BasePolicy):
    policy_filter_code = models.TextField(null=True, blank=True)
    policy_conditional_code = models.TextField(null=True, blank=True)
    policy_action_code = models.TextField(null=True, blank=True)
    policy_failure_code = models.TextField(null=True, blank=True)
    
    policy_text = models.TextField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'communitypolicy'
        verbose_name_plural = 'communitypolicies'
        
    def clean(self):
        super().clean()
        if self.policy_action_code is None and self.policy_text is None:
            raise ValidationError('Code or text rule instructions are both None')

        
    def __str__(self):
        return ' '.join(['CommunityPolicy: ', self.explanation, 'for', self.community_integration.community_name])
    
    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            process = ProcessPolicy.objects.filter(proposal__status=Proposal.PASSED, community_integration=self.community_integration)
            p = self.proposal
            p.status = Proposal.PROPOSED
            p.save()
            
            super(CommunityPolicy, self).save(*args, **kwargs)
            
            if process.exists():
                policy = self
                exec(process[0].policy_code)

        else:   
            super(CommunityPolicy, self).save(*args, **kwargs)
    

# class VoteSystem(models.Model):
#     
#     class Meta:
#         abstract = True  


class UserVote(models.Model):
    
    user = models.ForeignKey(CommunityUser,
                              models.CASCADE)
    
    proposal = models.ForeignKey(Proposal,
                                models.CASCADE)
    
    boolean_value = models.BooleanField(null=True) # yes/no, selected/not selected
    
    