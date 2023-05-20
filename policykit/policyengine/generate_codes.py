import logging

logger = logging.getLogger(__name__)

def check_format_string(string):
    """ 
        Check whether the string contains any embedded variables or data, and format it accordingly 
        TODO: check whether the referenced variables or data are defined
    """
    import re
    curley_pattern = r"\{(.+?)\}"
    data_pattern = r"data\.([a-zA-Z_][a-zA-Z0-9_]*)"
    variable_pattern = r"variables\.([a-zA-Z_][a-zA-Z0-9_]*)"
    action_pattern = r"action\.([a-zA-Z_][a-zA-Z0-9_]*)"
    proposal_pattern = r"proposal\.([a-zA-Z_][a-zA-Z0-9_]*)"

    required_f_string = False
    for match in re.finditer(curley_pattern, string):
        match_str = match.group(0)
        content = match.group(1)
        logger.debug(f"Matched string: {match_str}, content {content}")
        
        data_match = re.match(data_pattern, content)
        if data_match and data_match.group(1).isidentifier():
            # e.g., check whether the contents are of the shape of data.board_members
            string  = string.replace(match_str, f"{{proposal.data.get(\"{data_match.group(1)}\")}}")
            required_f_string = True
        
        variable_match = re.match(variable_pattern, content)
        if variable_match:
            if variable_match.group(1).isidentifier():
                required_f_string = True
            else:
                logger.warning(f"Embedded codes in a f-string {match_str} is not a valid identifier")
        
        action_match = re.match(action_pattern, content)
        if action_match:
            if action_match.group(1).isidentifier():
                required_f_string = True
            else:
                logger.warning(f"Embedded codes in a f-string {match_str} is not a valid identifier")
        
        proposal_match = re.match(proposal_pattern, content)
        if proposal_match:
            if proposal_match.group(1).isidentifier():
                required_f_string = True
            else:
                logger.warning(f"Embedded codes in a f-string {match_str} is not a valid identifier")
                
    return string, required_f_string

def force_variable_types(value, variable):
    """
        when generating codes, we need to make sure the value specified by users (a string) are correctly embedded in the codes
        in accordance with the variable type (e.g., string, number, list of string, list of number) 
    """     
    value_codes = ""
    if not value:
        """
            For now we assume an empty string represents None in the execution codes 
            as we do not know whether an empty string is no input or actually an empty string
            
            We do not need to replace value with the default value of this variable here,
            as we load default values in the input box of the frontend, and if users make no change,
            the value will automatically be the default value.
        """
        value_codes = "None"
    else:
        if variable["is_list"]:
            if variable["type"] == "number" or variable["type"] == "float":
                # e.g., value = "1, 2, 3", then codes should be "[1, 2, 3]"
                value_codes = f"[{value}]"
            elif variable["type"] == "string":
                # e.g., value = "test1, test2, test3", then codes should be "[\"test1\", \"test2\", \"test3\"]"
                value_list = value.split(",")
                value_codes = "["
                for value in value_list:
                    value_codes += f"\"{value}\","
                value_codes = value_codes[:-1] # remove the last comma
                value_codes += "]"
            else:
                raise Exception(f"variable type {variable['type']} is not supported for list")
        else:
            if variable["type"] in ["number", "float", "timestamp"]:
                # e.g., value = "1", then codes should be "1" and we treat timestamp as an integer
                value_codes = f"{value}"
            elif variable["type"] == "string":
                # e.g., value = "test", then codes should be "\"test\""
                # an additional f is included so that variables inside the string can be evaluated
                
                # add safety check to make sure the string does not contain any malicious codes
                value, required_f_string = check_format_string(value)
                value_codes = f"f\"{value}\"" if required_f_string else f"\"{value}\""
            else:
                raise NotImplementedError
    return value_codes

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

def generate_filter_codes(filters):
    """
        Generate codes from a list of filters defined in JSON
        See examples of the parameter filters above 

        The generated codes will be in the shape of 
        if action.action_type == "slackpostmessage":
	        def CommunityUser_Role(role, object=None):
		        all_usernames_with_roles = [_user.username for _user in slack.get_users(role_names=[role])]
		        return (object.username in all_usernames_with_roles) if object else None, all_usernames_with_roles
	        def Text_Equals(text, object=None):
		        return object == text, None
	        return CommunityUser_Role("test", action.initiator)[0] and Text_Equals("test", action.text)[0]

    """

    from policyengine.models import FilterModule

    filter_codes = ""
    for action_filter in filters:
        # we first check whether the action is the one we want to apply filters to
        filter_codes += "if action.action_type == \"{action_type}\":\n\t".format(action_type = action_filter["action_type"])
        # one example: "if action.action_type == \"slackpostmessage\":\n\t
        
        now_codes = []
        function_calls = [] # a list of names of filter functions we will call in the end for each action type
        
        # only custom actions have the filter key
        for field, field_filter in action_filter.get("filter", {}).items():
            """  e.g.,
                    "initiator": {
                        "kind": "CommunityUser",
                        "name": "Role",
                        "variables": [
                            {
                                "name": "role",
                                "label": "Which role users should have?",
                                "entity": "Role",
                                "default_value": null,
                                "is_required": true,
                                "prompt": "",
                                "type": "string",
                                "is_list": false
                            }
                        ],
                        "platform": "slack"
                    },
            """
            if field_filter:
                filter = FilterModule.objects.filter(kind=field_filter["kind"], name=field_filter["name"]).first()
                if not filter:
                    raise Exception(f"Filter {field_filter['kind']}_{field_filter['name']} not found")
                
                field_filter["codes"] = filter.codes
                parameters_codes = "object, " + ", ".join([var["name"]  for var in field_filter["variables"]])
                now_codes.append(
                    "def {kind}_{name}({parameters}):".format(
                        kind = field_filter["kind"], 
                        name = field_filter["name"],
                        parameters = parameters_codes
                    )
                ) # result example: def CommunityUser_Role(role, object=None):


                module_codes = field_filter["codes"].format(platform=field_filter["platform"])
                # in case the exact platform such as slack is used in the codes
                module_codes = ["\t" + line for line in module_codes.splitlines()]
                # because these codes are put inside a function, we need to indent them

                now_codes.extend(module_codes)

                parameters_called = []
                parameters_called.append("action.{field}".format(field=field)) # action.initiator
                for var in field_filter["variables"]:
                    # we need to make sure the value specified by users (a string) are correctly embedded in the codes
                    parameters_called.append(force_variable_types(var["value"], var))
                parameters_called = ", ".join(parameters_called) # action.initiator, "test"
                function_calls.append(
                    "{kind}_{name}({parameters})".format(
                        kind = field_filter["kind"], 
                        name = field_filter["name"], 
                        parameters = parameters_called
                    )
                )
        if now_codes:
            filter_codes += "\n\t".join(now_codes) + "\n\treturn " + " and ".join(function_calls) + "\n"
        else:
            filter_codes += "return True\n"
    return filter_codes