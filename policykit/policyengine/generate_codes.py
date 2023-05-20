def extract_action_types(filters):
    """ 
    extract all ActionTypes defined in a list of CustomActions JSON
    e.g.,
        [
            {
                "action_type": "slackpostmessage",
                "filter": {
                    "initiator": {
                        "kind": "CommunityUser",
                        "name": "Role",
                        "variables": [
                                {
                                    "name": "role",
                                    "type": "string",
                                    "value": "hello"
                                }
                            ]
                    },
                    "text": {
                        "kind": "Text",
                        "name": "Startswith",
                        "variables": [
                            {
                                "name": "word",
                                "type": "string",
                                "value": "test"
                            }
                        ]
                    }
                },
                "community_name": null
            },
            {
                "action_type": "slackrenameconversation"
            }
        ],
    """
    from policyengine.models import ActionType
    action_types = []
    for filter in filters:
        action_codename = filter["action_type"]
        action_type = ActionType.objects.filter(codename=action_codename).first()
        if action_type:
            action_types.append(action_type)
    return action_types