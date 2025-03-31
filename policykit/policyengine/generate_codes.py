import logging
import policyengine.utils as Utils
logger = logging.getLogger(__name__)

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
                if not Utils.check_code_variables(value):
                    value_codes = f"\"{value}\""
                else:
                    value = Utils.validate_fstrings(value)
                    value_codes = f"f\"{value}\""
            else:
                raise NotImplementedError
    return value_codes

def extract_action_types(custom_actions):
    """ 
    extract all ActionTypes defined in a list of CustomActions JSON
    e.g.,
        [
            {
                "action_types": ["slackpostmessage"] or ["slackpostmessage", "slackrenameconversation"]
                "filter": {
                    "view": "form",
                    "form": {
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
                    }

                    or

                    "view": "codes",
                    "codes": "...."
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
    for custom_action in custom_actions:
        action_codenames = custom_action["action_types"]
        for action_codename in action_codenames:
            action_type = ActionType.objects.filter(codename=action_codename).first()
            if action_type:
                action_types.append(action_type)

    return action_types

def generate_filter_codes(custom_actions):
    """
        Generate codes from a list of custom actions defined in JSON
        See examples of the parameter custom actions above 

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

    custom_actions_codes = ""
    for custom_action in custom_actions:
        print(custom_action)
        if custom_action['filter']["view"] == "codes":
            # if the view is codes, we just use the codes as it is
            custom_actions_codes += custom_action['filter']["codes"]
            continue

        # then if the view is form, we need to generate codes from the filter
        
        assert len(custom_action["action_types"]) == 1, "Currently only support one action type for each custom action in the form view"
        # we first check whether the action is the one we want to apply filters to
        custom_actions_codes += "if action.action_type == \"{action_type}\":\n\t".format(action_type = custom_action["action_types"][0])
        # one example: "if action.action_type == \"slackpostmessage\":\n\t
        
        now_codes = []
        function_calls = [] # a list of names of filter functions we will call in the end for each action type
        
        # only custom actions have the filter key
        form_filters = custom_action["filter"]["form"]
        for field, field_filter in form_filters.items():
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
            custom_actions_codes += "\n\t".join(now_codes) + "\n\treturn " + " and ".join(function_calls) + "\n"
        else:
            custom_actions_codes += "return True\n"
    if not custom_actions_codes:
        custom_actions_codes = "pass"
    return custom_actions_codes

'''
def generate_initialize_codes(data):
    """
        Help generate codes for calculating static data, as codes for dynamic data have already been included in check codes
    """
    initialize_codes = ""
    for datum in data:
        if(datum["dynamic"] == False):
            initialize_codes += datum["codes"] 
            # e.g. board_members = [user.username for user in slack.get_users(role_names=[variables[\"board_role\"]])]
            initialize_codes += "proposal.data.set(\"{name}\", {name})".format(name=datum["name"]) + "\n"
            # e.g. proposal.set("board_members", board_members)
    if not initialize_codes:
        initialize_codes = "pass"
    return initialize_codes
'''


def generate_check_codes(checks):
    """
        a list of checks defined in JSON
        We assume the last check is the one representing the referenced procedure, 
        and we will use its name to find the procedure
        e.g. 
        [
            {
                "name": "Enforce procedure time restrictions",
                "description": "..."
            },
            {
                "name": "Consesus Voting",
                "description": "..."
            }
        ],
    """
    from policyengine.models import Transformer, Procedure
    # in cases when the user writes a policy without any checks (e.g., a if-then rules)
    if(len(checks) == 0):
        return "pass"
    
    check_codes = ""
    for check in checks[:-1]:
        check_module = Transformer.objects.filter(name=check["name"]).first()
        if not check_module:
            raise Exception(f"When generating check codes, Transformer {check['name']} not found")
        check_codes += check_module.codes
    
    # the last check is the one representing the referenced procedure
    procedure = Procedure.objects.filter(name=checks[-1]["name"]).first()
    if not procedure:
        raise Exception(f"When generating check codes, Procedure {checks[-1]['name']} not found")
    procedure_check = procedure.loads("check")
    if "codes" not in procedure_check:
        raise Exception(f"When generating check codes, Procedure {checks[-1]['name']} does not have check codes")
    check_codes += procedure_check["codes"]

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
    elif execution["platform"] == "slack" and execution["action"] == "initiate_advanced_vote":
        codes = "slack.initiate_advanced_vote(candidates={candidates}, options={options}, users={users}, channel={channel}, title={title}, details={details})".format(
                    candidates = execution["candidates"],
                    options = execution["options"],
                    users = execution["users"],
                    channel = execution["channel"],
                    title=execution["title"],
                    details = execution["details"]
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
    elif platform == "slack" and vote_type == "initiate_advanced_vote":
        return [
            {
                "name": "candidates",
                "label": "Candidates that users can vote for",
                "entity": None,
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": True
            },
            {
                "name": "options",
                "label": "Options that users can select for each candidate",
                "entity": None,
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": True
            },
            {
                "name": "users",
                "label": "Eligible voters",
                "entity": "SlackUser",
                "default_value": "",
                "is_required": False,
                "prompt": "",
                "type": "string",
                "is_list": True
            },
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
                "name": "title",
                "label": "Message to be posted when initiating the vote",
                "entity": None,
                "default_value": "",
                "is_required": True,
                "prompt": "",
                "type": "string",
                "is_list": False
            },
            {
                "name": "details",
                "label": "Message to be posted when initiating the vote",
                "entity": None,
                "default_value": "",
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
        if value.startswith("variables") or value.startswith("proposal") or value.startswith("action"):
            # We do nothing there as we also use the attribute style of variables
            execution[name] = value
        elif value.startswith("data"):
            # value e.g., data.board_members
            datum_name = value.split(".", 1)[1]
            execution[name] = f"proposal.data.get(\"{datum_name}\")"
        else:
            """ 
                if the value is not a PolicyVariable or data, we need to convert it to the expected type
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
                "view": "form",
                "action": "initiate_vote",
                "vote_message": "variables.vote_message",
                "vote_type": "boolean",
                "users": "variables.users",
                "channel": "variables.vote_channel",
                "platform": "slack"
            }
        ]
    or
        [
            {   
                "view": "form",
                "action": "slackpostmessage",
                "text": "LeijieWang",
                "channel": "test-channel",
                "frequency": "60"
            }
        ]

    or [
            {
                "view": "form",
                "codes: "...."
            }
        ]
    """
    from policyengine.utils import find_action_cls
    execution_codes = []
    comment_only = True
    for execution in executions:
        execution_view = execution.get("view", "form")
        if execution_view == "codes":
            codes = execution["codes"]
            comment_only = False
        elif execution_view == "form":
            codes = ""
            # if "frequency" in execution:
            #     # if the execution has a frequency, then it is a recurring execution
            #     # we need to add the frequency to the execution
            #     duration_variable = "last_time_" + execution["action"]
            #     codes += f"if not proposal.data.get(\"{duration_variable}\"):\n\tproposal.data.set(\"{duration_variable}\", proposal.get_time_elapsed().total_seconds())\nif proposal.vote_post_id and ((proposal.get_time_elapsed().total_seconds() - proposal.data.get(\"{duration_variable}\")) > int({execution['frequency']})) * 60:\n\tproposal.data.set(\"duration_variable\", proposal.get_time_elapsed().total_seconds())\n\t"

            if execution["action"] == "initiate_vote" or execution["action"] == "initiate_advanced_vote":
                execute_variables = initiate_execution_variables(execution["platform"], execution["action"])
                execution = force_execution_variable_types(execution, execute_variables)
                codes += generate_initiate_votes(execution)
                comment_only = False
            elif execution["action"] == "revert_actions":
                codes += "action.revert()"
                comment_only = False
            elif execution["action"] == "execute_actions":
                codes += "# actions are reverted in the policy engine by default\n"
            else:
                # currently only support slackpostmessage
                action_codename = execution["action"]
                this_action = find_action_cls(action_codename)
                if hasattr(this_action, "execution_codes"):
                    execute_variables = this_action.EXECUTE_VARIABLES
                    execution = force_execution_variable_types(execution, execute_variables)
                    codes += this_action.execution_codes(**execution)
                    comment_only = False
                else:
                    raise NotImplementedError
        else:
            logger.error(f"view {execution['view']} is not supported")
            raise NotImplementedError

        execution_codes.append(codes)
    
    if comment_only:
        # if the code is only comments, we need to add a pass statement at the end
        return "\n".join(execution_codes) + "pass\n"
    else:
        return "\n".join(execution_codes) + "\n"
