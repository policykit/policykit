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
    if value not in ['assign', 'revoke']:
        raise ValidationError("Action must be 'assign' or 'revoke'")

class PutMembersRequestSerializer(serializers.Serializer):
    action = serializers.CharField(validators=[validate_action_field])
    role = serializers.IntegerField()  # pk of role to assign
    members = serializers.ListField(child=serializers.IntegerField())  # list of user pks to assign to role
