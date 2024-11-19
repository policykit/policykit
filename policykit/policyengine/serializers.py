import rest_framework.serializers as serializers
from rest_framework.exceptions import ValidationError

class CommunityRoleSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source='__str__')

class MemberSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField(source='__str__')
    avatar = serializers.CharField()
    roles = CommunityRoleSummarySerializer(many=True, source='get_roles')

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

class CommunityDashboardSerializer(serializers.Serializer):
    roles = DashboardRoleSummarySerializer(many=True, source='get_roles')
    community_docs = CommunityDocSerializer(source='get_documents', many=True)
    platform_policies = PolicySummarySerializer(many=True, source='get_platform_policies')
    constitution_policies = PolicySummarySerializer(many=True, source='get_constitution_policies')
    trigger_policies = PolicySummarySerializer(many=True, source='get_trigger_policies')
    proposals = ProposalSummarySerializer(many=True)
    name = serializers.CharField(source="community_name")
