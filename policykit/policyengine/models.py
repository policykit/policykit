from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.govinterface.models import LogEntry
from polymorphic.models import PolymorphicModel
from django.core.exceptions import ValidationError
from policyengine.views import *


class CommunityIntegration(PolymorphicModel):
    community_name = models.CharField('team_name', 
                              max_length=1000)
    
    user_group = models.ForeignKey(Group, models.CASCADE)


class CommunityUser(User, PolymorphicModel):
        
    readable_name = models.CharField('readable_name', 
                                      max_length=300)
    
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
    
        
    access_token = models.CharField('access_token', 
                                     max_length=300, 
                                     unique=True)
    
        
    def save(self, *args, **kwargs):      
        super(User, self).save(*args, **kwargs)
        p1 = Permission.objects.get(name='Can add process')
        p2 = Permission.objects.get(name='Can add rule')
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
        
        
        
class CommunityAction(PolymorphicModel):
    ACTION = None
    AUTH = 'app'
    
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
    
    author = models.ForeignKey(CommunityUser,
                                models.CASCADE)
    
    community_post_id = models.CharField('community_post_id', 
                                         max_length=300)
    
    
    def api_call(self, values, call):
        data = urllib.parse.urlencode(values)
        data = data.encode('utf-8')
        call_info = call + '?'
        req = urllib.request.Request(call_info, data)
        resp = urllib.request.urlopen(req)
        res = json.loads(resp.read().decode('utf-8'))
        logger.info(res)
        return res
    
    def revert(self, values, call):
        _ = self.api_call(values, call)
        
    def post_rule(self, values, call):
        rule = RulePolicy.objects.filter(community_integration=self.community_integration,
                                         status=Policy.PASSED)
        if rule.count() > 0:
            rule = rule[0]
            rules_message = "This action is governed by the following rule: " + rule.explanation + '. Vote with :thumbsup: or :thumbsdown: on this post.'
            values['text'] = rules_message
            res = self.api_call(values, call)
            
            self.community_post_id = res['ts']
            self.save()
            
            
    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            super(CommunityAction, self).save(*args, **kwargs)
            action_policy = ActionPolicy.objects.create(community_integration=self.community_integration,
                                                      author=self.author,
                                                      status=Policy.PROPOSED,
                                                      content_type=self.polymorphic_ctype,
                                                      object_id=self.id,
                                                      action=ActionPolicy.ADD,
                                                      )

        else:   
            super(CommunityAction, self).save(*args, **kwargs) 
        
        
class Policy(PolymorphicModel):
    community_integration = models.ForeignKey(CommunityIntegration, 
        models.CASCADE,
        verbose_name='community_integration',
    )
    
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
    
    
class ProcessPolicy(Policy):    
    process_code = models.TextField()
    explanation = models.TextField(null=True, blank=True)
    
    # if this condition is met, then the RulePolicy status is set to passed
    
    class Meta:
        verbose_name = 'process'
        verbose_name_plural = 'processes'

        
    def __str__(self):
        return ' '.join(['Process: ', self.explanation, 'for', self.community_integration.community_name])
    
    
    
class RulePolicy(Policy):
    rule_code = models.TextField(null=True, blank=True)
    
    rule_text = models.TextField(null=True, blank=True)
    
    explanation = models.TextField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'rule'
        verbose_name_plural = 'rules'
        
    def clean(self):
        super().clean()
        if self.rule_code is None and self.rule_text is None:
            raise ValidationError('Code or text rule instructions are both None')

        
    def __str__(self):
        return ' '.join(['Rule: ', self.explanation, 'for', self.community_integration.community_name])
    
    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            process = ProcessPolicy.objects.filter(status=Policy.PASSED, community_integration=self.community_integration)
            self.status = Policy.PROPOSED
            
            super(RulePolicy, self).save(*args, **kwargs)
            
            if process.exists():
                exec(process[0].process_code)

        else:   
            super(RulePolicy, self).save(*args, **kwargs)
    
    
class ActionPolicy(Policy):
    content_type = models.ForeignKey(
        ContentType,
        models.CASCADE,
        verbose_name='content type',
    )
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    ADD = 'add'
    CHANGE = 'change'
    VIEW = 'view'
    DELETE = 'delete'
    
    ACTIONS = [
            (ADD, 'add'),
            (CHANGE, 'change'),
            (VIEW, 'view'),
            (DELETE, 'delete')
        ]
    
    action = models.CharField(choices=ACTIONS, max_length=10)
    
    
    class Meta:
        verbose_name = 'action'
        verbose_name_plural = 'actions'

    def __str__(self):
        return ' '.join(['Action: ', self.action, str(self.content_type), 'to', self.community_integration.community_name])

    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            self.status = Policy.PROPOSED
            
            super(ActionPolicy, self).save(*args, **kwargs)
            
            action = self
            for rule in RulePolicy.objects.filter(status=Policy.PASSED, community_integration=self.community_integration):
                exec(rule.rule_code)

        else:   
            super(ActionPolicy, self).save(*args, **kwargs)
        
        

class UserVote(models.Model):
    
    user = models.ForeignKey(CommunityUser,
                              models.CASCADE)
    
    policy = models.ForeignKey(Policy,
                                models.CASCADE)
    
    value = models.BooleanField(null=True)
    
    
    
    