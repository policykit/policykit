.. _start:


Sample Policies
###############

This is a library of example Platform Policies to get started.

Slack Policies
==============

Add examples here

Discourse Policies
==================

Add examples here

Discord Policies
================

Add examples here

Metagov Policies
================

Metagov policies can be defined for any community.
It doesn't matter whether the PolicyKit instance is installed to Slack, Discourse, Discord, or Reddit, as long as
Metagov is enabled and the required Plugins are enabled and configured in the PolicyKit settings page.

Use SourceCred to gate posts on a Discourse topic
-------------------------------------------------

When a user makes a post on Discourse topic 116, look up their Cred value.
If they don't have at least 1 Cred, delete the post, and
send them a message explaining why.

**Required Metagov Plugins**: ``sourcecred`` ``discourse``

**Filter:**

.. code-block:: python

    return action.action_codename == "metagovaction" and \
        action.event_type == "discourse.post_created" and \
        action.event_data["topic_id"] == 116

**Initialize:**

.. code-block:: python

    # store the required cred threshold so we can access it later
    action.data.set("required_cred", 1)

**Notify:** ``pass``

**Check:**

.. code-block:: python

    username = action.initiator.metagovuser.external_username
    params = {"username": username}
    result = metagov.perform_action("sourcecred.user-cred", params)
    user_cred = result["value"]

    # store the user cred value so we can access it later
    action.data.set("cred", user_cred)

    return PASSED if user_cred >= action.data.get("required_cred") else FAILED


**Pass:** ``pass``

**Fail:**

.. code-block:: python

    # Delete the post
    metagov.perform_action("discourse.delete-post", {"id": action.event_data["id"]})

    # Let the user know why
    user_cred = action.data.get("cred")
    required_cred = action.data.get("required_cred")
    post_url = action.event_data["url"]
    discourse_username = action.initiator.metagovuser.external_username
    params = {
        "title": "PolicyKit deleted your post",
        "raw": f"The following post was deleted because you only have {user_cred} Cred, and at least {required_cred} Cred is required for posting on that topic: {post_url}",
        "is_warning": False,
        "target_usernames": [discourse_username]
    }
    metagov.perform_action("discourse.create-message", params)

    
Vote on Open Collective expense in Open Collective
--------------------------------------------------

**Required Metagov Plugins**: ``opencollective``

**Filter:**

.. code-block:: python

    return action.action_codename == "metagovaction" and \
        action.event_type == "opencollective.expense_created"	

**Initialize:**

.. code-block:: python

    # Kick off the Metagov governance process called "opencollective.vote"

    expense_url = action.event_data['url']
    description = action.event_data['description']
    parameters = {
        "title": f"Vote on expense '{description}'",
        "details": f"Thumbs-up or thumbs-down react to vote on expense {expense_url}"
    }
    result = metagov.start_process("opencollective.vote", parameters)
    vote_url = result.outcome.get("vote_url")
    # [elided] optionally, message users on whatever platform to tell them to vote at vote_url

**Notify:** ``pass``


**Check:**

.. code-block:: python

    # When 60 minutes has passed, close the process and decide whether this policy has PASSED or FAILED

    import datetime

    if action.proposal.get_time_elapsed() > datetime.timedelta(minutes=60):
        result = metagov.close_process()
        yes_votes = result.outcome["votes"]["yes"]
        no_votes = result.outcome["votes"]["no"]
        return PASSED if yes_votes >= no_votes else FAILED

    return None


**Pass:**

.. code-block:: python

    # Approve the expense

    parameters = {
        "expense_id": action.event_data["id"],
        "action": "APPROVE"
    }
    metagov.perform_action("opencollective.process-expense", parameters)

**Fail:**

.. code-block:: python

    # Reject the expense

    parameters = {
        "expense_id": action.event_data["id"],
        "action": "REJECT"
    }
    metagov.perform_action("opencollective.process-expense", parameters)


Add a NEAR DAO proposal
-----------------------

When a new Discourse topic is created with tag ``dao-proposal``, add a new proposal to the community's NEAR DAO.
Uses the `near.call <https://prototype.metagov.org/redoc/#operation/near.call>`_ action.

**Required Metagov Plugins**: ``discourse`` ``near``

**Filter:**

.. code-block:: python

    return action.action_codename == "metagovaction" and \
        action.event_type == "discourse.topic_created" and \
        "dao-proposal" in action.event_data["tags"]

**Initialize:** ``pass``

**Notify:** ``pass``

**Check:** ``return PASSED``

**Pass:**

.. code-block:: python

    title = action.event_data["title"]
    topic_url = action.event_data["url"]

    # How we find the wallet ID for the Discourse user? Hard-coding the target for this example.
    discourse_username = action.initiator.metagovuser.external_username
    

    params = {
        "method_name": "add_proposal",
        "args": {
            "proposal": {
                "description": f"Pay {discourse_username} for {title}. Link: {topic_url}",
                "kind": {"type": "Payout",  "amount": "100" },
                "target": "dev.mashton.testnet"
            }
        },
        "gas": 100000000000000,
        "amount": 100000000000000
    }
    try:
        result = metagov.perform_action("near.call", params)
    except Exception as e:
        debug(str(e))

    debug(f"NEAR call: {result.get("status")}")

**Fail:** ``pass``


Vote on Discourse Proposal in Loomio
------------------------------------

When a new Discourse topic is created with tag ``special-proposal``, start a new vote in Loomio
to decide whether to accept or reject the proposal. If rejected, delete the topic. This example
uses the Metagov ``discourse`` plugin, which is distinct from the PolicyKit Discourse integration.
This policy can be defined for any PolicyKit community (a Slack community, for example).

**Required Metagov Plugins**: ``discourse`` ``loomio``

**Filter:**

.. code-block:: python

    return action.action_codename == "metagovaction" and \
        action.event_type == "discourse.topic_created" and \
        "special-proposal" in action.event_data["tags"]

**Initialize:**

.. code-block:: python

    title = action.event_data["title"]
    discourse_username = action.initiator.metagovuser.external_username
    topic_url = action.event_data["url"]

    import datetime
    closing_at = (action.proposal.proposal_time + datetime.timedelta(days=3)).strftime("%Y-%m-%d")

    # Kick off a vote in Loomio
    parameters = {
        "title": f"Vote on adding proposal '{title}'",
        "details": f"proposed by {discourse_username} on Discourse: {topic_url}",
        "options": ["agree", "disagree"],
        "closing_at": closing_at
    }
    result = metagov.start_process("loomio.poll", parameters)
    poll_url = result.outcome.get("poll_url")

    # Make a post in Discourse to let people know where to vote
    params = {
        "topic_id": action.event_data["id"],
        "raw": f"Loomio vote started at {poll_url}",
    }
    metagov.perform_action("discourse.create-post", params)

**Notify:** ``pass``

**Check:**

.. code-block:: python

    result = metagov.get_process()

    # send debug log of intermediate results. visible in PolicyKit app at /logs.,
    debug("Loomio result: " + str(result))

    if result.status == "completed":
        agrees = result.outcome["votes"]["agree"]
        disagrees = result.outcome["votes"]["disagree"]
        outcome_text = f"{agrees} people agreed, and {disagrees} people disagreed."
        action.data.set("outcome_text", outcome_text)

        return PASSED if agrees > disagrees else FAILED

    return None # pending




**Pass:**

.. code-block:: python

    text = action.data.get('outcome_text')
    params = {
        "topic_id": action.event_data["id"],
        "raw": f"{text} The proposal is approved!",
    }
    metagov.perform_action("discourse.create-post", params)

**Fail:**

.. code-block:: python

    text = action.data.get('outcome_text')
    params = {
        "topic_id": action.event_data["id"],
        "raw": f"{text} The proposal is rejected. Deleting this topic."
    }
    metagov.perform_action("discourse.create-post", params)

    # Delete the topic
    metagov.perform_action("discourse.delete-topic", {"id": action.event_data["id"]})
    
