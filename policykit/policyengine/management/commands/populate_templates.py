from django.core.management.base import BaseCommand
from policyengine.models import Community, Policy, PolicyVariable, ActionType


class Command(BaseCommand):
    help = "Populate templates for Collective Voice"

    def handle(self, *args, **options):
        desc = """
        Expenses on Open Collective will be up for a vote on Slack before being approved.
        """

        filter_func = """
        return True
        """

        check = """
        if not proposal.vote_post_id:
            return None
        yes_votes = proposal.get_yes_votes().count()
        no_votes = proposal.get_no_votes().count()

        if no_votes >= int(variables[\"no_votes_to_reject\"]):
            return FAILED
        if yes_votes >= int(variables[\"yes_votes_to_approve\"]):
            return PASSED\n
        return PROPOSED
        """

        notify = """
        discussion_channel = variables[\"slack_channel_id\"]
        message = f\"Vote on <{action.url}|this request> for funds: {action.description}\"
        slack.initiate_vote(text=message, channel=discussion_channel)
        slack.post_message(text=\"Discuss here, if needed.\", channel=discussion_channel, thread_ts=proposal.vote_post_id)\n
        link = f\"<a href='{proposal.vote_url}'>on Slack</a>\"
        text = f\"Thank you for submitting a request! A vote has been started {link}.\"
        opencollective.post_message(text=text, expense_id=action.expense_id)\n
        """

        policy, created = Policy.objects.get_or_create(
            kind="trigger",
            name="collectivevoicebase",
            filter=filter_func,
            initialize="pass",
            check=check,
            notify=notify,
            success="opencollective.process_expense(action=\"APPROVE\", expense_id=action.expense_id)\n\nyes_votes = proposal.get_yes_votes().count()\nno_votes = proposal.get_no_votes().count()\nmessage = f\"Expense approved. The vote passed with {yes_votes} for and {no_votes} against.\"\n\n# comment on the expense\nopencollective.post_message(text=message, expense_id=action.expense_id)\n\n# update the Slack thread\nslack.post_message(text=message, channel=variables[\"slack_channel_id\"], thread_ts=proposal.vote_post_id)\n",
            fail="opencollective.process_expense(action=\"REJECT\", expense_id=action.expense_id)\n\nyes_votes = proposal.get_yes_votes().count()\nno_votes = proposal.get_no_votes().count()\nmessage = f\"Expense rejected. The vote failed with {yes_votes} for and {no_votes} against.\"\n\n# comment on the expense\nopencollective.post_message(text=message, expense_id=action.expense_id)\n\n# update the Slack thread\nslack.post_message(text=message, channel=variables[\"slack_channel_id\"], thread_ts=proposal.vote_post_id)\n",
            # is_template=True,
            description=desc,
            community=Community.objects.first()
        )
        if created:
            action_type, _ = ActionType.objects.get_or_create(codename="expensecreated")
            policy.action_types.add(action_type)


            # Expense filtering variable
            PolicyVariable.objects.create(
                name="expense_type", label="Expense Type", default_value="All", is_required=True,
                prompt="Type of expense to vote on", type="string", policy=policy)

            # Voting Variables
            PolicyVariable.objects.create(
                name="num_voters", label="Number of Voters", default_value=1, is_required=True,
                prompt="How many total voters?", type="number", policy=policy)
            PolicyVariable.objects.create(
                name="eligible_voters", label="Who can vote", default_value=[], is_required=True,
                prompt="Who can vote?", type="list", policy=policy)
            PolicyVariable.objects.create(
                name="yes_votes_to_approve", label="Yes Votes Needed To Approve", default_value=1, is_required=True,
                prompt="If this number of YES votes is hit, the expense is approved", type="number", policy=policy)
            PolicyVariable.objects.create(
                name="no_votes_to_reject", label="No Votes Needed to Reject", default_value=1, is_required=True,
                prompt="If this number of NO votes is hit, the expense is rejected", type="number", policy=policy)
            PolicyVariable.objects.create(
                name="slack_channel_id", label="Slack Channel ID", default_value="", is_required=True,
                prompt="Which Slack Channel to use?", type="string", policy=policy)


        check2 = """
        if not proposal.vote_post_id:
            return None
        yes_votes = proposal.get_yes_votes().count()
        no_votes = proposal.get_no_votes().count()

        if no_votes >= int(variables[\"no_votes_to_reject\"]):
            return FAILED
        if yes_votes >= int(variables[\"yes_votes_to_approve\"]):
            return PASSED\n
        return PROPOSED
        """

        