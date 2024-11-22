from django.shortcuts import render
import json
import logging


from django.contrib.auth import authenticate, get_user, login
from django.contrib.auth.decorators import login_required, permission_required
from django.http import (Http404, HttpResponse, HttpResponseBadRequest,
                         JsonResponse)

import policyengine.utils as Utils


logger = logging.getLogger(__name__)



def create_blank_policytemplate(community):
    from policyengine.models import PolicyTemplate
    policytemplate = PolicyTemplate.objects.create(
        kind="trigger",
        name=f"collectivevoice_{community.id}",
    )
    return policytemplate

def get_collectivevoice_policytemplate_from_request(request):
    from policyengine.models import PolicyTemplate
    user = get_user(request)
    community = user.community.community

    try:
        policytemplate = PolicyTemplate.objects.get(name=f"collectivevoice_{community.id}")
    except:
        policytemplate = create_blank_policytemplate(community=community)
    return policytemplate


@login_required
def collectivevoice_home(request):
    """
    Show the home screen for CV
    If they've already gone through the flow, show policy details.
    Otherwise, show buttons to edit EXPENSES, VOTING TEMPLATE, and FOLLOW UP

    Operates on three main objects:
        - a CustomAction (with FilterModules),
        - a Procedure,
        - and extra_executions attribute of the PolicyTemplate
    """
    from policyengine.models import PolicyTemplate
    from integrations.slack.models import SlackCommunity
    from integrations.opencollective.models import OpencollectiveCommunity
    from django.core import serializers

    policy_id = request.GET.get("policy_id")
    try:
        pt = PolicyTemplate.objects.get(pk=policy_id)
    except:
        pt = PolicyTemplate.objects.create(name="collectivevoice_tmp")



    expenses_set = False
    filter_names = []
    if len(pt.custom_actions.all()) > 0 or len(pt.action_types.all()) > 0:
        expenses_set = True
        for action in pt.custom_actions.all():
            try:
                d = action.__dict__['filter']
                filters = list(json.loads(d).keys())
                filter_names += filters
            except Exception as e:
                logger.debug(str(e))
            
    filter_names_str = ",".join(filter_names)


    voting_set = False
    procedure_name = None
    if pt.procedure is not None:
        voting_set = True
        procedure_name = pt.procedure.name        

    followup_set = False
    if len(pt.extra_executions) > 2: # default is '{}'
        followup_set = True

    pt_data = serializers.serialize('json', [pt,])

    user = get_user(request)
    slack_community = SlackCommunity.objects.get(community=user.community.community) 
    opencollective_community = OpencollectiveCommunity.objects.get(community=user.community.community) 
    
    return render(request, "collectivevoice/home.html", {
        'policytemplate': pt_data,
        'policy_id': pt.id,
        'expenses_set': expenses_set,
        'voting_set': voting_set,
        'followup_set': followup_set,
        'procedure_name': procedure_name,
        'filter_names_str': filter_names_str,
        'slack_community': slack_community,
        'opencollective_community': opencollective_community
    })

@login_required
def collectivevoice_edit_expenses(request):
    """
    User can select which expenses will trigger votes
    """
    from policyengine.models import PolicyActionKind, FilterModule
    policy_id = request.GET.get("policy_id")

    filter_parameters = {}
    new_actions = {}

    user = get_user(request)
    # only get Trigger actions for OpenCollective
    actions = Utils.get_action_types(user.community.community, kinds=[PolicyActionKind.TRIGGER])
    app_name = "opencollective"
    action_list = actions[app_name]
    new_action_list = []
    for action_code, verbose_name in action_list:
        parameter = Utils.get_filter_parameters(app_name, action_code)
        # only show actions that have filter parameters
        if parameter:
            filter_parameters[action_code] = parameter
            new_action_list.append((action_code, verbose_name))
    # only show apps that have at least one action with filter parameters
    if new_action_list:
        new_actions[app_name] = new_action_list

    filter_modules = {}
    for app_name in new_actions:
        filter_modules[app_name] = {}
        filters_per_app = FilterModule.objects.filter(platform__in=[app_name, "All"])
        # get distinct filter kinds for each app
        filter_kinds = list(filters_per_app.values_list('kind', flat=True).distinct())
        for kind in filter_kinds:
            filter_modules[app_name][kind] = []
            for filter in filters_per_app.filter(kind=kind):
                filter_modules[app_name][kind].append({
                    "pk": filter.pk, 
                    "name": filter.name,
                    "description": filter.description, 
                    "variables": filter.loads("variables")
                })

    entities = Utils.load_entities(user.community)
    return render(request, "collectivevoice/edit_expenses.html", {
        "trigger": True,
        "actions": new_actions, # this variable is only used in html template and therefore no dump is needed
        "filter_parameters": json.dumps(filter_parameters), # this variable is used in javascript and therefore needs to be dumped
        "filter_modules": json.dumps(filter_modules),
        "entities": json.dumps(entities),
        "policy_id": policy_id,
    })

@login_required
def collectivevoice_edit_voting(request):
    """
    c.f. design_procedures
    """
    from policyengine.models import Procedure      

    procedure_objects = Procedure.objects.all()
    procedures = []
    procedure_details = []
    # keep variables in a different dict simply to avoid escaping problems of nested quotes
    # the first is to use directly in template rendering, while the second is to use in javascript
    for template in procedure_objects:
        procedures.append({
            "name": template.name, 
            "pk": template.pk, 
            "platform": template.platform,     
            "description": template.description

        })
            
        procedure_details.append({
            "name": template.name, 
            "pk": template.pk, 
            "variables": template.loads("variables"),
        })
    
    # Only Slack for v0.1 of CollectiveVoice
    platform_names = ["slack"]

    user = get_user(request)

    trigger = request.GET.get("trigger", "false")
    policy_id = request.GET.get("policy_id")
    entities = Utils.load_entities(user.community, get_slack_users=True)
    return render(request, "collectivevoice/edit_voting.html", {
        "procedures": json.dumps(procedures),
        "procedure_details": json.dumps(procedure_details),
        "platforms": platform_names,
        "trigger": trigger,
        "policy_id": policy_id,
        "entities": json.dumps(entities)
    })

@login_required
def collectivevoice_edit_followup(request):
    """cf no-code design_executions"""
    policy_id = request.GET.get("policy_id", None)
    # "success" or "fail"

    if policy_id:
        user = get_user(request)
        executable_actions, execution_variables = Utils.extract_executable_actions(user.community.community)
        entities = Utils.load_entities(user.community)
        return render(request, "collectivevoice/edit_followup.html", {
            "policy_id": policy_id,
            "executions": executable_actions,
            "execution_variables": json.dumps(execution_variables),
            "entities": json.dumps(entities)
        })



@login_required
def create_custom_action(request):
    """see no-code create_custom_action for latest approach"""
    from policyengine.models import CustomAction, ActionType, PolicyTemplate, FilterModule

    data = json.loads(request.body)
    filters = data.get("filters", None)

    pt = PolicyTemplate.objects.get(id=data.get("policy_id"))
    
    pt.custom_actions.all().delete()

    # only create a new PolicyTemplate instance when there is at least one filter specified
    if filters and len(filters) > 0:
        is_trigger = True
        for filter in filters:
            action_type = filter.get("action_type")
            action_type = ActionType.objects.filter(codename=action_type).first()
            
            action_specs = filter.get("filter")
            '''
                check whether the value of each action_specs is an empty string
                create a new CustomAction instance for each selected action that has specified filter parameters
                and only search the action_type for any selected action without specified filter parameters
                an example of a action_specs:
                    {
                        "initiator":{"filter_pk":"72", "platform": "slack", "variables":{"role":"test"}},
                        "text":{}
                    }
                    
            '''
            empty_filter = not any(["filter_pk" in value for value in list(action_specs.values()) ])
            filter_JSON = {}
            if empty_filter:
                pt.action_types.add(action_type)
            else:
                custom_action = CustomAction.objects.create(
                    action_type=action_type, is_trigger=is_trigger
                )
                for field, filter_info in action_specs.items():
                    if not filter_info:
                        filter_JSON[field] = None
                    else:
                        filter_module = FilterModule.objects.filter(pk=int(filter_info["filter_pk"])).first()
                        # create a filter JSON object with the actual value specified for each variable
                        filter_JSON[field] = filter_module.to_json(filter_info["variables"])
                        # to faciliate the generation of codes for custom actions, we store the platform of each filter
                        filter_JSON[field]["platform"] = filter_info["platform"]
                custom_action.dumps("filter", filter_JSON)
                custom_action.save()
                pt.custom_actions.add(custom_action)                

        pt.save()
        return JsonResponse({"policy_id": pt.pk, "status": "success"})
    else:
        return JsonResponse({"status": "fail"})
    
@login_required  
def create_procedure(request):
    '''
        Create the procedure field of a PolicyTemplate instance based on the request body.
        We also add variables defined in the selected procedure to the new policytemplate instance

        Parameters:
            request.body: 
                A Json object in the shape of
                {  
                    "procedure_index": an integer, which represents the primary key of the selected procedure;
                    "policy_id": an integer, which represents the primary key of the policy that we are creating
                    "procedure_variables": a dict of variable names and their values
                }
    '''
    from policyengine.models import Procedure, PolicyTemplate

    data = json.loads(request.body)
    procedure_index = data.get("procedure_index", None)
    policy_id = data.get("policy_id", None)
    if procedure_index and policy_id:
        # why first?
        procedure = Procedure.objects.filter(pk=procedure_index).first()
        pt = PolicyTemplate.objects.filter(pk=policy_id).first()
        if pt and procedure:
            logger.debug("clearing old variables in case user is changing the voting rule")
            pt.variables = "[]"
            pt.data = "[]"

            logger.debug("creating variables for the new policy")
            pt.procedure = procedure
            pt.add_variables(procedure.loads("variables"), data.get("procedure_variables", {}))
            pt.add_descriptive_data(procedure.loads("data"))
            pt.save()

            return JsonResponse({"status": "success", "policy_id": pt.pk})
    return JsonResponse({"status": "fail"})


@login_required
def customize_procedure(request):
    """
        Help render the customize procedure page
    """
    from policyengine.models import CheckModule, PolicyTemplate
    
    # prepare information about module templates
    checkmodules_objects = CheckModule.objects.all()
    checkmodules = []
    checkmodules_details = []
    for template in checkmodules_objects:
        checkmodules.append((template.pk, template.name))
        checkmodules_details.append({
            "name": template.name, 
            "pk": template.pk, 
            "variables": template.loads("variables")
        })

    # prepare information about extra executions that are supported
    user = get_user(request)
    executable_actions, execution_variables = Utils.extract_executable_actions(user.community.community)

    
    trigger = request.GET.get("trigger", "false")
    policy_id = request.GET.get("policy_id")
    entities = Utils.load_entities(user.community)
    data = {
            "checkmodules": checkmodules,
            "checkmodules_details": json.dumps(checkmodules_details),
            "executions": executable_actions,
            "execution_variables": json.dumps(execution_variables),
            "trigger": trigger,
            "policy_id": policy_id,
            "entities": json.dumps(entities)
        }

    now_policy = PolicyTemplate.objects.filter(pk=policy_id).first()
    data["policy_variables"] = json.dumps(
            now_policy.loads("variables") if now_policy else {}
        )
    return render(request, "no-code/customize_procedure.html", data)

@login_required
def create_customization(request):
    """
        Add extra check modules and extra actions to the policy template

        parameters:
            request.body: e.g.,
                {
                    "policy_id": 1,
                    
                    "module_index": 1,
                    "module_data": {
                        "duration": ...
                    }

                    "action_data": {
                        "check"/"notify": {
                            "action": "slackpostmessage",
                            "channel": ...,
                            "text": ...
                        }
                    }
                }
    """
    from policyengine.models import CheckModule, PolicyTemplate

    data = json.loads(request.body)
    
    policy_id = data.get("policy_id", None)
    new_policy = PolicyTemplate.objects.filter(pk=policy_id).first()
    if new_policy:
        module_index = data.get("module_index", None)
        module_template = CheckModule.objects.filter(pk=module_index).first()
        if module_template:
            new_policy.add_check_module(module_template)
            new_policy.add_variables(module_template.loads("variables"), data.get("module_data", {}))
            new_policy.add_descriptive_data(module_template.loads("data"))
        action_data = data.get("action_data", None)
        if action_data:
            new_policy.add_extra_actions(action_data)
        new_policy.save()
        return JsonResponse({"status": "success", "policy_id": new_policy.pk})
    return JsonResponse({"status": "fail"})


@login_required  
def create_execution(request):
    """
        Add executions to success or fail blocks of the policytemplate instance

        parameters:
            request.body: e.g.,
                "action_data":  
                    {
                        "success"/"fail": {
                            "action": "slackpostmessage",
                            "channel": ...,
                            "text": ...
                        }
                    }
    """
    from policyengine.models import PolicyTemplate

    data = json.loads(request.body)
    policy_id = data.get("policy_id", None)
    pt = PolicyTemplate.objects.filter(pk=policy_id).first()
    if pt:
        action_data = data.get("action_data", {})
        if action_data:
            pt.add_extra_actions(action_data)
            pt.save()
        return JsonResponse({"status": "success", "policy_id": pt.pk})
    return JsonResponse({"status": "fail"})

@login_required 
def policy_overview(request):
    """
        help render the policy overview page where users can fill in the policy name and description,
        and also see the policy template in json format
    """
    from policyengine.models import PolicyTemplate

    policy_id = request.GET.get("policy_id", None)
    created_policy = PolicyTemplate.objects.filter(pk=policy_id).first()
    if created_policy:
        created_policy_json = created_policy.to_json()
        return render(request, "collectivevoice/policy_overview.html", {
            "policy": json.dumps(created_policy_json),
            "policy_id": policy_id,
        })

@login_required  
def create_overview(request):
    """
        Add policy name and description to the policy template instance

        parameters:
            request.body: 
                {
                    "policy_id": 1,
                    data: {
                        "name": "policy name",
                        "description": "policy description"
                    }
                }
    """
    from policyengine.models import PolicyTemplate
    request_body = json.loads(request.body)
    policy_id = int(request_body.get("policy_id", -1))
    policy_template = PolicyTemplate.objects.filter(pk=int(policy_id)).first()
    if policy_template :
        data = request_body.get("data")
        policy_template.name = data.get("name", "")
        policy_template.description = data.get("description", "")
        # NMV: hard-code for CollectiveVoice
        policy_template.kind = "trigger"
        policy_template.save()

        user = get_user(request)
        new_policy = policy_template.create_policy(user.community.community, policy_template)
        return JsonResponse({"policy_id": new_policy.pk, "policy_type": (new_policy.kind).capitalize(), "status": "success"})
    else:
        return JsonResponse({"status": "fail"})
    
def policy_from_request(request, key_name = 'policy'):
    policy_id = request.GET.get(key_name)
    from policyengine.models import Policy
    try:
        return Policy.objects.get(pk=policy_id)
    except Policy.DoesNotExist:
        raise Http404("Policy does not exist")

def collectivevoice_success(request):
    """Shows success page when no-code editing is finished."""
    policy = policy_from_request(request)
    return render(request, "collectivevoice/success.html", {
        "policy": policy
    })