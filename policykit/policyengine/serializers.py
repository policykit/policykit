import rest_framework.serializers as serializers
from rest_framework.exceptions import ValidationError

class MembersRoleSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source='role_name')
    user_ids = serializers.PrimaryKeyRelatedField(many=True, read_only=True, source='user_set')
    # users = serializers.ListField(child=serializers.IntegerField(), source='user_set.all.values_list("pk", flat=True)')

class MemberSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source='__str__')
    avatar = serializers.CharField()

class MembersSerializer(serializers.Serializer):
    roles = MembersRoleSummarySerializer(many=True, source='get_roles')
    members =  MemberSummarySerializer(many=True, source='get_members')

def validate_action_field(value):
    if value not in ['Add', 'Remove']:
        raise ValidationError("Action must be 'Add' or 'Remove'")

class PutMembersRequestSerializer(serializers.Serializer):
    action = serializers.CharField(validators=[validate_action_field])
    role = serializers.IntegerField()  # pk of role to assign
    members = serializers.ListField(child=serializers.IntegerField())  # list of user pks to assign to role

class DashboardRoleSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source='role_name')
    description = serializers.CharField()
    number_of_members = serializers.IntegerField(source='user_set.count', min_value=0)

class PolicySummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    description = serializers.CharField()
    # platform = serializers.CharField()

class ActionSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    action_type = serializers.CharField()
    description = serializers.CharField()

class InitiatorSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    readable_name = serializers.CharField()

class ProposalSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    status = serializers.CharField()
    proposal_time = serializers.DateTimeField()  # TODO check this is utc
    is_vote_closed = serializers.BooleanField()
    action = ActionSummarySerializer()
    initiator = InitiatorSummarySerializer(source='action.initiator')
    policy = PolicySummarySerializer()

class CommunityDocSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    text = serializers.CharField()

class CommunityUserSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    readable_name = serializers.CharField()


class ActionSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    initiator = CommunityUserSummarySerializer()
    str = serializers.CharField(source='__str__')


class CommunityDashboardSerializer(serializers.Serializer):
    roles = DashboardRoleSummarySerializer(many=True, source='get_roles')
    community_docs = CommunityDocSerializer(source='get_documents', many=True)
    platform_policies = PolicySummarySerializer(many=True, source='get_platform_policies')
    constitution_policies = PolicySummarySerializer(many=True, source='get_constitution_policies')
    trigger_policies = PolicySummarySerializer(many=True, source='get_trigger_policies')
    pending_proposals = ProposalSummarySerializer(many=True)
    completed_proposals = ProposalSummarySerializer(many=True)
    name = serializers.CharField(source="community_name")
    # Don't include governable actions for now, instead we use proposals
    # governable_actions = ActionSummarySerializer(many=True, source="get_governable_actions")

class LogEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    create_datetime = serializers.DateTimeField()
    level = serializers.IntegerField()
    action = serializers.CharField(source='action_str')
    policy = serializers.CharField(source='policy_str')
    msg = serializers.CharField()

class LogsSerializer(serializers.Serializer):
    logs = serializers.SerializerMethodField()
    
    # this method will look for functions named "get_<field_name>"
    def get_logs(self, community):
        from django_db_logger.models import EvaluationLog
        logs = EvaluationLog.objects.filter(community=community).order_by('-create_datetime')
        return LogEntrySerializer(logs, many=True).data
