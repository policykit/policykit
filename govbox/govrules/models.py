from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
# from django.contrib.govinterface.models import LogEntry
from polymorphic.models import PolymorphicModel
from govrules.views import execute_proposal


class CommunityIntegration(PolymorphicModel):
    community_name = models.CharField('team_name', 
                              max_length=1000)
    
    user_group = models.ForeignKey(Group, models.CASCADE)


class CommunityUser(User, PolymorphicModel):
        
    readable_name = models.CharField('readable_name', 
                                      max_length=300)
    
    community_integration = models.ForeignKey(CommunityIntegration,
                                   models.CASCADE)
        
    def save(self, *args, **kwargs):      
        super(User, self).save(*args, **kwargs)
        p1 = Permission.objects.get(name='Can add process')
        p2 = Permission.objects.get(name='Can add rule')
        p3 = Permission.objects.get(name='Can add action')
        self.user_permissions.add(p1)
        self.user_permissions.add(p2)
        self.user_permissions.add(p3)
        
        


class Measure(PolymorphicModel):
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
    
    PROPOSED = 'proposed'
    FAILED = 'failed'
    PASSED = 'passed'
    
    STATUS = [
            (PROPOSED, 'proposed'),
            (FAILED, 'failed'),
            (PASSED, 'passed')
        ]
    
    status = models.CharField(choices=STATUS, max_length=10)
    
    class Meta:
        abstract = True
    
    
    
class ProcessMeasure(Measure):    
    code = models.TextField()
    explanation = models.TextField(null=True)
    
    # if this condition is met, then the RuleMeasure status is set to passed
    
    class Meta:
        verbose_name = 'process'
        verbose_name_plural = 'processes'

        
    def __str__(self):
        return ' '.join(['Process: ', self.explanation, 'for', self.community_integration.community_name])
    
    
    
class RuleMeasure(Measure):
    rule_code = models.TextField()
    
    rule_text = models.TextField()
    
    explanation = models.TextField(null=True)
    
    class Meta:
        verbose_name = 'rule'
        verbose_name_plural = 'rules'
        
    def __str__(self):
        return ' '.join(['Rule: ', self.explanation, 'for', self.community_integration.community_name])
    
    def save(self, *args, **kwargs):
        if not self.pk:
            # Runs only when object is new
            process = ProcessMeasure.objects.filter(status=Measure.PASSED, community_integration=self.community_integration)
            self.status = Measure.PROPOSED
            
            super(RuleMeasure, self).save(*args, **kwargs)
            
            if process.exists():
                exec(process[0].code)

        else:   
            super(RuleMeasure, self).save(*args, **kwargs)
    
    
class ActionMeasure(Measure):
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
        super(ActionMeasure, self).save(*args, **kwargs)
        
        for rule in RuleMeasure.objects.filter(community_integration=self.community_integration):
            exec(rule.code)


    