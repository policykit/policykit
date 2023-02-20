from policyengine.models import PolicyVariable

class VoteModule():
    def createModuleVariables(policy):
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
