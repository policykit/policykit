from django.core.management.base import BaseCommand
from policyengine.models import Policy, PolicyVariable, ActionType


class Command(BaseCommand):
    help = "Populate templates for collective voice code"

    def handle(self, *args, **options):

        desc = """
        Posts OpenCollective expenses to Slack for voting.
        You set: minimum number of yes votes, maximum number of no votes, eligible voters.
        After a three hour voting window, 
        expense will be approved if enough yes votes and few enough no votes were cast.
        Once the vote is resolved, posts to both Slack thread and the OpenCollective expense thread with vote results.
        """

        check = """
        if not proposal.vote_post_id:
            return None
        yes_votes = proposal.get_yes_votes().count()
        no_votes = proposal.get_no_votes().count()
        time_elapsed = proposal.get_time_elapsed()
        if time_elapsed < datetime.timedelta(hours=3):
            return None
        if no_votes >= int(variables[\"no_votes_to_reject\"]):
            return FAILED
        if yes_votes >= int(variables[\"yes_votes_to_approve\"]):
            return PASSED\n
        return PROPOSED
        """

        notify = """
        discussion_channel = variables[\"slack_channel_id\"]
        message = f\"Vote on whether to approve <{action.url}|this request> for funds: {action.description}\"
        slack.initiate_vote(text=message, channel=discussion_channel)
        # Start a discussion thread on the voting message
        slack.post_message(text=\"Discuss here, if needed.\", channel=discussion_channel, thread_ts=proposal.vote_post_id)\n
        # Add a comment to the expense on Open Collective with a link to the Slack vote
        link = f\"<a href='{proposal.vote_url}'>on Slack</a>\"
        text = f\"Thank you for submitting a request! A vote has been started {link}.\"
        opencollective.post_message(text=text, expense_id=action.expense_id)\n
        """

        policy, created = Policy.objects.get_or_create(
            kind="trigger",
            name="Expense Voting Template",
            filter="return True",
            initialize="pass",
            check=check,
            notify=notify
            success="# approve the expense\nopencollective.process_expense(action=\"APPROVE\", expense_id=action.expense_id)\n\nyes_votes = proposal.get_yes_votes().count()\nno_votes = proposal.get_no_votes().count()\nmessage = f\"Expense approved. The vote passed with {yes_votes} for and {no_votes} against.\"\n\n# comment on the expense\nopencollective.post_message(text=message, expense_id=action.expense_id)\n\n# update the Slack thread\nslack.post_message(text=message, channel=variables[\"slack_channel_id\"], thread_ts=proposal.vote_post_id)\n",
            fail="# reject the expense\nopencollective.process_expense(action=\"REJECT\", expense_id=action.expense_id)\n\nyes_votes = proposal.get_yes_votes().count()\nno_votes = proposal.get_no_votes().count()\nmessage = f\"Expense rejected. The vote failed with {yes_votes} for and {no_votes} against.\"\n\n# comment on the expense\nopencollective.post_message(text=message, expense_id=action.expense_id)\n\n# update the Slack thread\nslack.post_message(text=message, channel=variables[\"slack_channel_id\"], thread_ts=proposal.vote_post_id)\n",
            is_template=True,
            description=desc
        )
        if created:
            action_type, _ = ActionType.objects.get_or_create(codename="expensecreated")
            policy.action_types.add(action_type)

            PolicyVariable.objects.create(
                name="yes_votes_to_approve", label="Yes Votes Needed To Approve", default_value=1, is_required=True,
                prompt="If this number of YES votes is hit, the expense is approved", type="number", policy=policy)
            PolicyVariable.objects.create(
                name="no_votes_to_reject", label="No Votes Needed to Reject", default_value=1, is_required=True,
                prompt="If this number of NO votes is hit, the expense is rejected", type="number", policy=policy)
            PolicyVariable.objects.create(
                name="slack_channel_id", label="Slack Channel ID", default_value="", is_required=True,
                prompt="Which Slack Channel to use?", type="string", policy=policy)
            
        
        # desc = """
        # For testing: add a very simple policy so that when you post "ping" in Slack,
        # the PolicyKit app will respond "pong". Except you can customize the "pong" message!
        # """
        # policy, created = Policy.objects.get_or_create(
        #     kind="trigger",
        #     name="Say 'ping', Get a 'pong' Back Test Example",
        #     filter='return action.text == "ping"',
        #     initialize='slack.post_message(variables["pong_message"])', 
        #     check='return PASSED',
        #     notify='pass',
        #     fail='pass',
        #     is_template=True,
        #     description=desc
        # )
        # if created:
        #     action_type, _ = ActionType.objects.get_or_create(codename="slackpostmessage")
        #     policy.action_types.add(action_type)

        #     PolicyVariable.objects.create(
        #         name="pong_message", label="What to say in response to ping", default_value="pong", is_required=True,
        #         prompt="What to say in response to ping", type="string", policy=policy)