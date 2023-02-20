

class VoteModule():
    def createModuleVariables(policy):
        from policyengine.models import PolicyVariable
        PolicyVariable.objects.create(
            name="duration", label="when the vote is closed (in minutes)", default_value=0, is_required=True,
            prompt="when the vote is closed (in minutes); an empty value represents that the vote is closed as long as the success or failure is reached", 
            type="number", policy=policy
        )

        PolicyVariable.objects.create(
            name="channel", label="Which channel should we post the vote", default_value="", is_required=True,
            prompt="Which channel should we post the vote; an empty value represents that the vote is cast in the channel where the command is posted", 
            type="string", policy=policy
        )

        PolicyVariable.objects.create(
            name="users", label="Who should be eligible to vote", default_value="", is_required=True,
            prompt="Who should be eligible to vote: an empty value represents that all people in the channel are eligible to vote. If there are multiple users, separate them by commas", 
            type="string", policy=policy
        )

        PolicyVariable.objects.create(
            name="minimum_yes_required", label="How many number of yes votes are required to reach success", default_value=1, is_required=True,
            prompt="How many number of yes votes are required to reach success", 
            type="number", policy=policy
        )
        
        PolicyVariable.objects.create(
            name="maximum_no_allowed", label="How many number of no votes are allowed before we call a failure", default_value=1, is_required=True,
            prompt="How many number of no votes are allowed before we call a failure", 
            type="number", policy=policy
        )

        PolicyVariable.objects.create(
            name="vote_message", label="Message to be posed in the channel when the vote starts", 
            default_value="Start a yes-no vote: vote with :thumbsup: or :thumbsdown: on this post.", is_required=True,
            prompt="Message to be posed in the channel when the vote starts", 
            type="string", policy=policy
        )

        PolicyVariable.objects.create(
            name="success_message", label="Message to be posed in the channel when the vote passes", 
            default_value="Proposal to vote passed", is_required=True,
            prompt="Message to be posed in the channel when the vote passes", 
            type="string", policy=policy
        )
        
        PolicyVariable.objects.create(
            name="failure_message", label="Message to be posed in the channel when the vote fails", 
            default_value="Proposal to vote failed", is_required=True,
            prompt="Message to be posed in the channel when the vote fails", 
            type="string", policy=policy
        )

    def createTemplatePolicies():
        policyDict = dict()
        policyDict["description"]="Voting templates: design your own vote logic"

        policyDict["filter"] = 'return action.text.startswith("vote")';
        
        policyDict["initialize"]='if not variables[\"channel\"]:\n  variables[\"channel\"] = action.channel\nif variables[\"users\"]:\n  variables[\"users\"] = variables[\"users\"].split(\",\")\nvariables[\"duration\"] = int(variables[\"duration\"])\nvariables[\"minimum_yes_required\"] = int(variables[\"minimum_yes_required\"])\nvariables[\"maximum_no_allowed\"] = int(variables[\"maximum_no_allowed\"])', 
        policyDict["check"]='if not proposal.vote_post_id:\n  return None\n\nif variables[\"duration\"] > 0:\n  time_elapsed = proposal.get_time_elapsed()\n  if time_elapsed < datetime.timedelta(minutes=variables[\"duration\"]):\n    return None\n\nyes_votes = proposal.get_yes_votes(users=variables[\"users\"]).count()\nno_votes = proposal.get_no_votes(users=variables[\"users\"]).count()\nlogger.debug(f\"{yes_votes} for, {no_votes} against\")\nif yes_votes >= variables[\"minimum_yes_required\"]:\n  return PASSED\nelif no_votes >= variables[\"maximum_no_allowed\"]:\n  return FAILED\n\nreturn PROPOSED',
        policyDict["notify"]='slack.initiate_vote(text=variables[\"vote_message\"], channel=variables[\"channel\"], users=variables[\"users\"])',
        
        policyDict["success"]='slack.post_message(text=variables[\"success_message\"], channel=variables[\"channel\"], thread_ts=proposal.vote_post_id)',
        policyDict["fail"]='slack.post_message(text=variables[\"failure_message\"], channel=variables[\"channel\"], thread_ts=proposal.vote_post_id)\n',
        

        return policyDict