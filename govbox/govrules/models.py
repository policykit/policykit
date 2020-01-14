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



    
    
    
class Post(models.Model):
    
    community = models.ForeignKey(CommunityIntegration, 
        models.CASCADE,
        verbose_name='community',
    )
    
    author = models.ForeignKey(
        User,
        models.CASCADE,
        verbose_name='author',
    )
    
    text = models.TextField()
    
    
    class Meta:
        verbose_name = 'post'
        verbose_name_plural = 'post'

    def __str__(self):
        return ' '.join([self.author.username, 'wrote', self.community.name])


    