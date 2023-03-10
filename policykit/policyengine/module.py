from django.db import models
import json
from policyengine.models import (
    CommunityPlatform,
    CustomAction,
    Procedure,
    Execution,
)

class PolicyTemplateFactory():

    
    def create_builtin_procedure_templates():
        """
            Create procedute templates for a given platform
        """

        if Procedure.objects.all().count() > 1:
            return;
    
        variables_for_simple_vote_procedure = {
                "duration": {
                    "name": "duration",
                    "label": "when the vote is closed (in minutes)",
                    "default_value": 0,
                    "is_required": True,
                    "prompt": "when the vote is closed (in minutes); an empty value represents that the vote is closed as long as the success or failure is reached",
                    "type": "number",
                },
                "channel": {
                    "name": "channel",
                    "label": "Which channel should we post the vote",
                    "default_value": "",
                    "is_required": True,
                    "prompt": "Which channel should we post the vote; an empty value represents that the vote is cast in the channel where the command is posted",
                    "type": "string",
                },
                "users": {
                    "name": "users",
                    "label": "Who should be eligible to vote",
                    "default_value": "",
                    "is_required": True,
                    "prompt": "Who should be eligible to vote: an empty value represents that all people in the channel are eligible to vote. If there are multiple users, separate them by commas",
                    "type": "string",
                },
                "minimum_yes_required": {
                    "name": "minimum_yes_required",
                    "label": "How many number of yes votes are required to reach success",
                    "default_value": 1,
                    "is_required": True,
                    "prompt": "How many number of yes votes are required to reach success",
                    "type": "number",
                },
                "maximum_no_allowed": {
                    "name": "maximum_no_allowed",
                    "label": "How many number of no votes are allowed before we call a failure",
                    "default_value": 1,
                    "is_required": True,
                    "prompt": "How many number of no votes are allowed before we call a failure",
                    "type": "number",
                },
                "vote_message": {
                    "name": "vote_message",
                    "label": "Message to be posed in the channel when the vote starts",
                    "default_value": "Start a yes-no vote: vote with :thumbsup: or :thumbsdown: on this post.",
                    "is_required": True,
                    "prompt": "Message to be posed in the channel when the vote starts",
                    "type": "string",
                }
            }

        simple_vote_procedure = {
            "name": "simple vote procedure duplicate",
            "initialize_code": 'if not variables[\"channel\"]:\n  variables[\"channel\"] = action.channel\n', 
            "check_code": 'if not proposal.vote_post_id:\n  return None\n\nif variables[\"duration\"] > 0:\n  time_elapsed = proposal.get_time_elapsed()\n  if time_elapsed < datetime.timedelta(minutes=variables[\"duration\"]):\n    return None\n\nyes_votes = proposal.get_yes_votes(users=variables[\"users\"]).count()\nno_votes = proposal.get_no_votes(users=variables[\"users\"]).count()\nlogger.debug(f\"{yes_votes} for, {no_votes} against\")\nif yes_votes >= variables[\"minimum_yes_required\"]:\n  return PASSED\nelif no_votes >= variables[\"maximum_no_allowed\"]:\n  return FAILED\n\nreturn PROPOSED',
            "notify_code": 'slack.initiate_vote(text=variables[\"vote_message\"], channel=variables[\"channel\"], users=variables[\"users\"])',
            "variables_dict": json.dumps(variables_for_simple_vote_procedure)
        }
        Procedure.objects.create(**simple_vote_procedure)
        
        simple_vote_procedure["name"] = "another simple vote procedure"
        Procedure.objects.create(**simple_vote_procedure)

        
        

        