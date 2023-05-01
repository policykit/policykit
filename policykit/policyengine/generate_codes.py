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
                value_codes = f"\"{value}\""
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
                        "codes": "all_usernames_with_roles = [_user.username for _user in {platform}.get_users(role_names=[role])]\nreturn (object.username in all_usernames_with_roles) if object else None, all_usernames_with_roles\n",
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
                        "codes": "return object.startswith(word), None",
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

    filter_codes = ""
    for action_filter in filters:
        # we first check whether the action is the one we want to apply filters to
        filter_codes += "if action.action_type == \"{action_type}\":\n\t".format(action_type = action_filter["action_type"])
        # one example: "if action.action_type == \"slackpostmessage\":\n\t
        
        now_codes = []
        function_calls = [] # a list of names of filter functions we will call in the end for each action type
        
        # only custom actions have the filter key; use get in case the filter key is not defined
        for field, field_filter in action_filter.get("filter", {}).items():
            """  e.g.,
                    "initiator": {
                        "kind": "CommunityUser",
                        "name": "Role",
                        "codes": "all_usernames_with_roles = [_user.username for _user in {platform}.get_users(role_names=[role])]\nreturn (object.username in all_usernames_with_roles) if object else None, all_usernames_with_roles\n",
                        "variables": [
                            {
                            "name": "role",
                            "type": "string",
                            "value": "test"
                            }
                        ],
                        "platform": "slack"
                    },
            """
            if field_filter:
                
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
                    if var["type"] == "number":
                        parameters_called.append(var["value"]) # "1" will be embedded as an integer 1 as required
                    else:
                        parameters_called.append("\"{}\"".format(var["value"]))
                parameters_called = ", ".join(parameters_called) # "test", action.initiator
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

def generate_check_codes(checks):
    """
        e.g. 
        [
            {
                "name": "Enforce procedure time restrictions",
                "codes": "if int(variables[\"duration\"]) > 0:\n  time_elapsed = proposal.get_time_elapsed()\n  if time_elapsed < datetime.timedelta(minutes=int(variables[\"duration\"])):\n    return None\n\n"
            },
            {
                "name": "main",
                "code": "if not proposal.vote_post_id:\n  return None\n\nyes_votes = proposal.get_yes_votes(users=variables[\"users\"]).count()\nno_votes = proposal.get_no_votes(users=variables[\"users\"]).count()\nlogger.debug(f\"{yes_votes} for, {no_votes} against\")\nif yes_votes >= int(variables[\"minimum_yes_required\"]):\n  return PASSED\nelif no_votes >= int(variables[\"maximum_no_allowed\"]):\n  return FAILED\n\nreturn PROPOSED\n"
            }
        ],
    """
    check_codes = ""
    for check in checks:
        check_codes += check["codes"]
    return check_codes

def generate_initiate_votes(execution):
    codes = ""
    
    if execution["platform"] == "slack" and execution["action"] == "initiate_vote":
        if execution.get("post_type") == "\"mpim\"":
            execution["channel"] = "None"
        
        codes = "slack.initiate_vote(users={users}, text={text}, post_type={post_type}, channel={channel}, options={options})".format(
                    users = execution["users"],
                    text = execution["vote_message"],
                    post_type = execution["post_type"],
                    channel = execution["channel"],
                    options = None
                )
    else:
        raise NotImplementedError
    return codes

def initiate_execution_variables(platform, vote_type):
    """
        Ideally, we should create a new BaseAction for initating votes in each integration, 
        and specify execution variables. But for now, we just hardcode them here, 
        since an addition of a new BaseAction may involve other more fundamental changes
    """
    if platform == "slack" and vote_type == "initiate_vote":
        return [
            {
                "name": "channel",
                "label": "Channel to post the vote",
                "entity": "SlackChannel",
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": False
            },
            {
                "name": "users",
                "label": "Eligible voters",
                "entity": "SlackUser",
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": True
            },
            {
                "name": "vote_message",
                "label": "Message to be posted when initiating the vote",
                "entity": None,
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": False
            },
            {
                "name": "post_type",
                "label": "How to post the vote in Slack",
                "entity": None,
                "default_value": "channel",
                "is_required": False,
                "prompt": "",
                "type": "string",
                "is_list": False
            }
        ]
    else:
        raise NotImplementedError

def force_execution_variable_types(execution, variables_details):
    """
        a wrapper function for force_variable_types when generating codes for an execution
    """

    for name, value in execution.items():
        if name in ["action", "platform"]:
            continue
        if value.startswith("variables"):
            # We do nothing there as we also use the attribute style of variables
            execution[name] = value
        else:
            """ 
                if the value is not a PolicyVariable, we need to convert it to the expected type
                Otherwise, this is not needed because we explictly force all PolicyVariables 
                to be expected types in EvaluationContext before executing codes 
            """
            var_detail = [var for var in variables_details if var["name"] == name]
            if len(var_detail) > 0:
                execution[name] = force_variable_types(value, var_detail[0])

    return execution

def generate_execution_codes(executions):

    """ 
    Help generate codes for a list of executions. 
    
    some examples of executions:
        [
            {
                "action": "initiate_vote",
                "vote_message": "variables[\"vote_message\"]",
                "vote_type": "boolean",
                "users": "variables[\"users\"]",
                "channel": "variables[\"vote_channel\"]",
                "platform": "slack"
            }
        ]
    or
        [
            {   
                "action": "slackpostmessage",
                "text": "LeijieWang",
                "channel": "test-channel",
                "frequency": "60"
            }
        ],
    """
    import re
    from policyengine.utils import find_action_cls

    execution_codes = []
    for execution in executions:
        for name, value in execution.items():
            if not (name in ["action", "platform"] or value.startswith("variables")):
                """
                    if the value is not a variable, then we need to add quotation marks
                    so that the variable will still be embedded as a string instead of a Python variable name
                    
                    We put the type validation in the `execution_codes` of each GovernableAction.
                    That is, if the value is expected to be an integer, 
                    each GovernableAction will convert the value to the integer by explictly calling `int()` in the generated codes
                """
                execution[name] = f"\"{value}\""
            
            # force the type of the value to be the same as the type of the corresponding variable as defined
            if value.startswith("variables"):
                # find in the list of variables of which the name is the same as the name here
                # extract "users" from the string variables[\"users\"]
                
                match = re.search(r'variables\[\"(.+?)\"\]', value)
                if match:
                    variable_name = match.group(1)
                matching_variables = list(filter(lambda var: var["name"] == variable_name, variables))
                if len(matching_variables) > 1:
                    raise ValueError("There should be only one variable with the same name")
                elif len(matching_variables) == 0:
                    raise ValueError("There should be at least one variable with the same name")
                else:
                    if matching_variables[0]["type"] == "number":
                        execution[name] = f"int({value})"

        if execution["action"] == "initiate_vote":
            execute_variables = initiate_execution_variables(execution["platform"], execution["action"])
            execution = force_execution_variable_types(execution, execute_variables)
            codes += generate_initiate_votes(execution)
        else:
            # currently only support slackpostmessage
            action_codename = execution["action"]
            this_action = find_action_cls(action_codename)
            if hasattr(this_action, "execution_codes"):
                execute_variables = this_action.EXECUTE_VARIABLES
                execution = force_execution_variable_types(execution, execute_variables)
                codes += this_action.execution_codes(**execution)
            else:
                raise NotImplementedError
        execution_codes.append(codes)
    return "\n".join(execution_codes) + "\n"
