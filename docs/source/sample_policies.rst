.. _start:


Sample Policies
###############

This is a library of example Platform Policies to get started.

Vote on renaming a Slack channel
--------------------------------

**Filter:**

.. code-block:: python

  return action.action_type == "slackrenameconversation"

**Initialize:** ``pass``

**Check:**

.. code-block:: python

  yes_votes = proposal.get_yes_votes().count()
  no_votes = proposal.get_no_votes().count()
  logger.info(f"{yes_votes} for, {no_votes} against")
  if yes_votes >= 1:
    return PASSED
  elif no_votes >= 1:
    return FAILED

  logger.info("No votes yet....")
  return None

**Notify:**

.. code-block:: python

  message = f"Should this channel be renamed to #{action.name}? Vote with :thumbsup: or :thumbsdown: on this post."
  slack.initiate_vote(proposal, template=message)

**Pass:**

.. code-block:: python

  text = f"Proposal to rename this channel to #{action.name} passed."
  slack.post_message(text=text, channel=action.channel, thread_ts=action.community_post)
  action.execute()

**Fail:**

.. code-block:: python

  text = f"Proposal to rename this channel to #{action.name} failed."
  slack.post_message(text=text, channel=action.channel, thread_ts=action.community_post)


Don't allow posts in Slack channel
----------------------------------

This could be extended to add any logic to determine who can post in a given channel.
Posts in the channel are auto-deleted, and the user is notified about why it happened.

**Filter:**

.. code-block:: python

  return action.action_type == "slackpostmessage" and action.channel == "ABC123"

**Initialize:** ``pass``

**Check:** ``return FAILED``

**Notify:** ``pass``

**Pass:** ``pass``

**Fail:**

.. code-block:: python

  # create an ephemeral post that is only visible to the poster
  message = f"Post was deleted because of policy '{policy.name}'"
  slack.post_message(
    channel=action.channel,
    users=[action.initiator],
    post_type="ephemeral",
    template=message
  )


Discord Message Filter
----------------------

In this tutorial, we will introduce policy creation by creating a policy that filters messages for a set of banned words.

::

 Note: In this tutorial, and the following tutorials, we will make use of the DiscordIntegration.
 If you are new to PolicyKit, we recommend following along in the DiscordIntegration so as not to
 become lost. However, it shouldn't pose too much of a challenge to emulate the steps in this
 tutorial in another integration, if you are up to the task.

To begin, we must log into the PolicyKit dashboard. You can use either our test server at `https://policykit.org/main/ <https://policykit.org/main/>`_ or your own custom PolicyKit server. To set up PolicyKit with your local Discord guild, please see our tutorial on setting up PolicyKit with Discord. Once you have finished setting up PolicyKit with Discord, you should install PolicyKit to your Discord server. For practice purposes, you should use the Testing starter kit, as it will allow you to instantly pass any policy you propose. When you have installed PolicyKit to your Discord server, you can sign in with Discord to view the PolicyKit dashboard.

From there, you should click the Propose Action button on the top right of the dashboard. On the following Actions screen, you should click the Platform Policies menu to drop down the list of platform policy actions. Select the Add Platform Policy option to view the Policy Editor.

Finally, you will be on the Policy Editor page, and we can begin creating our policy! First, choose a name and description for your policy. You can leave the description blank if you wish.

In PolicyKit, incoming actions are checked against the Filter block of each active policy. Each policy is only executed on the action if the policy's Filter block returns True. The Filter block returns False by default.

We only want our Message Filter policy to run on actions which are messages posted to the Discord channel we are monitoring. To check if the action is a posted message, we can check a property of the ``action`` object called ``action_type``. The codename for posting a message on Discord is ``"discordpostmessage"``. Thus, our Filter block is::

  if action.action_type == "discordpostmessage":
    return True

We want to check all posted messages to see if they contain any blacklisted words. For example, suppose we want to ban the words "minecraft", "amazon", and "facebook" (due to repeated spam). In the Check block of the policy, we can check the ``text`` property of the ``action`` object and see if a substring of the text is a banned word. If so, the policy will fail the action (``return FAILED``). Otherwise, it will pass the action (``return PASSED``). If we don't return anything, ``PROPOSED`` will be returned by default, representing an intermediate state. Our Check block is::

  for banned_word in ["minecraft", "amazon", "facebook"]:
    if banned_word in action.text:
      return FAILED
  return PASSED

All other fields can be left as their defaults; there is no need to modify them. Once you have finished typing this code into the policy editor, click "Propose Policy" to propose the policy to your community. Once it passes, try it out! See how you can extend the policy further. A couple ideas:
 * Check ``action.text`` against Google's Perspective API (which checks for spam, hate speech, etc.).
 * Instead of removing posts which violate the Message Filter, allow the community to vote on whether the post should be shown. Or wait for moderator approval before displaying the post.

Great job! You have created your first policy.

Discord Dice Rolling
--------------------

This will allow the user to roll a dice by typing the following command:
     !roll d[num_faces] +[num_modifier]
where num refers to a positive non-zero integer value. This command simulates rolling a dice with num_faces faces (e.g. d100 is a dice with 100 faces). The user can optionally add a modifier, which adds an integer value to the result of the dice roll. For example, +7 would add 7 to the result of the dice roll.

**Filter:**

.. code-block:: python

  if action.action_type != "DiscordPostMessage":
    return False
  tokens = action.text.split()
  if tokens[0] != "!roll":
    return False
  if len(tokens) < 2 or len(tokens) > 3:
    discord.post_message(text='not right number of tokens: should be 2 or 3', channel = "733209360549019688")
    return False
  return True

**Initialize:** ``pass``

**Check:**

.. code-block:: python

  import random
  tokens = action.text.split()
  channel = 733209360549019691
  if tokens[1][0] != "d":
    duscird.post_message(text='not have d', channel=channel)
    return FAILED
  if tokens[1][1:].isnumeric() == False:
    duscird.post_message(text='not numeric num faces', channel=channel)
    return FAILED
  num_faces = int(tokens[1][1:])
  num_modifier = 0
  if len(tokens) == 3:
    if tokens[2][0] != "+":
      duscird.post_message(text='not have +', channel=channel)
      return FAILED
    if tokens[2][1:].isnumeric() == False:
      duscird.post_message(text='not numeric num modifier', channel=channel)
      return FAILED
    num_modifier = int(tokens[2][1:])
  roll_unmodified = random.randint(1, num_faces)
  roll_modified = roll_unmodified + num_modifier
  proposal.data.set('roll_unmodified', roll_unmodified)
  proposal.data.set('roll_modified', roll_modified)
  return PASSED

**Notify:** ``pass``

**Pass:**

.. code-block:: python

  text = 'Roll: ' + str(proposal.data.get('roll_unmodified')) + " , Result: " + str(proposal.data.get('roll_modified'))
  discord.post_message(text=text, channel = "733209360549019688")

**Fail:**

.. code-block:: python

  text = 'Error: Make sure you format your dice roll command correctly!'
  discord.post_message(text=text, channel = "733209360549019688")

Discord Lottery / Raffle
------------------------

Allow users to vote on a "lottery" message, pick a random user as the lottery winner, and automatically notify the channel.

**Filter:**

.. code-block:: python

  if action.action_type != "DiscordPostMessage":
    return False
  tokens = action.text.split(" ", 1)
  if tokens[0] != "!lottery":
    return False
  if len(tokens) != 2:
    discord.post_message(text='need a lottery message', channel = "733209360549019688")
    return False
  proposal.data.set('message', tokens[1])
  return True

**Initialize:** ``pass``

**Notify:**

.. code-block:: python

  message = proposal.data.get('message')
  discord.initiate_vote(proposal, template=message, channel = "733209360549019688")

**Check:**

.. code-block:: python

  all_votes = proposal.get_yes_votes()
  num_votes = len(all_votes)
  if num_votes >= 3:
    return PASSED

**Pass:**

.. code-block:: python

  import random

  all_votes = proposal.get_yes_votes()
  num_votes = len(all_votes)
  winner = random.randint(0, num_votes)
  winner_name = all_votes[winner].user.readable_name
  message = "Congratulations! " + winner_name + " has won the lottery!"
  discord.post_message(text=message, channel = "733209360549019688")

**Fail:** ``pass``

Use SourceCred to gate posts on a Discourse topic
-------------------------------------------------

When a user makes a post on Discourse topic 116, look up their Cred value.
If they don't have at least 1 Cred, delete the post, and
send them a message explaining why.

**Required integrations**: ``sourcecred`` ``discourse``

**Filter:**

.. code-block:: python

    return action.event_type == "discourse.post_created" and \
        action.data["topic_id"] == 116

**Initialize:**

.. code-block:: python

    # store the required cred threshold so we can access it later
    proposal.data.set("required_cred", 1)

**Notify:** ``pass``

**Check:**

.. code-block:: python

    username = action.data["author"] # just an example, not actually the shape..
    user_cred = sourcecred.get_cred(username=username)

    # store the user cred value so we can access it later
    proposal.data.set("cred", user_cred)

    return PASSED if user_cred >= proposal.data.get("required_cred") else FAILED


**Pass:** ``pass``

**Fail:**

.. code-block:: python

    # Delete the post
    metagov.perform_action("discourse.delete-post", id=action.data["id"])

    # Let the user know why
    user_cred = proposal.data.get("cred")
    required_cred = proposal.data.get("required_cred")
    post_url = action.data["url"]
    username = action.data["author"]
    params = {
        "title": "PolicyKit deleted your post",
        "raw": f"The following post was deleted because you only have {user_cred} Cred, and at least {required_cred} Cred is required for posting on that topic: {post_url}",
        "is_warning": False,
        "target_usernames": [username]
    }
    metagov.perform_action("discourse.create-message", **params)


Vote on Open Collective expense
-------------------------------

When an expense is submitted in Open Collective, start a new conversation thread
in the Open Collective collective. Members can vote on the expense using thumbs-up
or thumbs-down emoji reactions. After 3 days, the expense is automatically approved
or rejected. This policy could be modified to use any other voting mechanism
(Loomio, Slack emoji-voting, Discourse polls, etc).

**Required integrations**: ``opencollective``

**Filter:**

.. code-block:: python

    return action.event_type == "opencollective.expense_created"

**Initialize:**

.. code-block:: python

    # Initiate governance process called "opencollective.vote"

    expense_url = action.data['url']
    description = action.data['description']
    result = metagov.start_process(
      "opencollective.vote",
      title=f"Vote on expense '{description}'",
      details=f"Thumbs-up or thumbs-down react to vote on expense {expense_url}"
    )
    vote_url = result.outcome.get("vote_url")
    # [elided] optionally, message users on whatever platform to tell them to vote at vote_url

**Notify:** ``pass``


**Check:**

.. code-block:: python

    # When 3 days have passed, close the process and decide whether this policy has PASSED or FAILED

    import datetime

    if proposal.get_time_elapsed() > datetime.timedelta(days=3):
        result = metagov.close_process()
        yes_votes = result.outcome["votes"]["yes"]
        no_votes = result.outcome["votes"]["no"]
        return PASSED if yes_votes >= no_votes else FAILED

    return None


**Pass:**

.. code-block:: python

    # Approve the expense
    opencollective.process_expense(expense_id=action.expense_id, action="APPROVE")

**Fail:**

.. code-block:: python

    # Reject the expense
    opencollective.process_expense(expense_id=action.expense_id, action="REJECT")


Add a NEAR DAO proposal
-----------------------

When a new Discourse topic is created with tag ``dao-proposal``, add a new proposal to the community's NEAR DAO.
Uses the `near.call <https://metagov.policykit.org/redoc/#operation/near.call>`_ action.

**Required integrations**: ``discourse`` ``near``

**Filter:**

.. code-block:: python

    return action.event_type == "discourse.topic_created" and \
        "dao-proposal" in action.data["tags"]

**Initialize:** ``pass``

**Notify:** ``pass``

**Check:** ``return PASSED``

**Pass:**

.. code-block:: python

    title = action.data["title"]
    topic_url = action.data["url"]

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

    result = metagov.perform_action("near.call", **params)
    logger.info(f"NEAR call: {result.get('status')}")

**Fail:** ``pass``


Vote on Discourse Proposal in Loomio
------------------------------------

When a new Discourse topic is created with tag ``special-proposal``, start a new vote in Loomio
to decide whether to accept or reject the proposal. If rejected, delete the topic. This example
uses the Metagov ``discourse`` plugin, which is distinct from the PolicyKit Discourse integration.
This policy can be defined for any PolicyKit community (a Slack community, for example).

**Required integrations**: ``discourse`` ``loomio``

**Filter:**

.. code-block:: python

    return action.event_type == "discourse.topic_created" and \
        "special-proposal" in action.data["tags"]

**Initialize:** ``pass``

**Notify:**

.. code-block:: python

    title = action.data["title"]
    discourse_username = action.initiator.metagovuser.external_username
    topic_url = action.data["url"]

    import datetime
    closing_at = proposal.proposal_time + datetime.timedelta(days=3)

    # Kick off a vote in Loomio
    loomio.initiate_vote(
      proposal,
      title=f"Vote on adding proposal '{title}'",
      details=f"proposed by {discourse_username} on Discourse: {topic_url}",
      options=["consent", "objection", "abstain"],
      closing_at=closing_at,
    )

    # The URL of the Loomio vote is stored on the proposal.
    poll_url = proposal.community_post

    # Make a post in Discourse to let people know where to vote
    params = {
        "topic_id": action.data["id"],
        "raw": f"Loomio vote started at {poll_url}",
    }
    metagov.perform_action("discourse.create-post", params)

**Check:**

.. code-block:: python

    consent = proposal.get_choice_votes(value="consent")
    objection = proposal.get_choice_votes(value="objection")
    abstain = proposal.get_choice_votes(value="abstain")

    vote_count_msg = f"{consent.count()} consent, {objection.count()} object, and {abstain.count()} abstain."

    # If the vote is still open in Loomio, return PROPOSED to indicate that the decision has not yet been reached
    if not proposal.is_vote_closed:
      logger.debug(f"Vote still open. {vote_count_msg}")
      return PROPOSED


    proposal.data.set("outcome_text", vote_count_msg)

    if abstain.count() < 2 and consent.count() > 5:
      return PASSED
    return FAILED


**Pass:**

.. code-block:: python

    text = proposal.data.get('outcome_text')
    params = {
        "topic_id": action.data["id"],
        "raw": f"{text} The proposal is approved!",
    }
    metagov.perform_action("discourse.create-post", params)

**Fail:**

.. code-block:: python

    text = proposal.data.get('outcome_text')
    params = {
        "topic_id": action.data["id"],
        "raw": f"{text} The proposal is rejected. Deleting this topic."
    }
    metagov.perform_action("discourse.create-post", params)

    # Delete the topic
    metagov.perform_action("discourse.delete-topic", {"id": action.data["id"]})

Vote on Adding Payment Pointers to a Web Monetization Rev Share config
----------------------------------------------------------------------

When a Discourse user adds a wallet to their profile, start a vote on whether to add the wallet to the community's `probabilistic revenue share config <https://webmonetization.org/docs/probabilistic-rev-sharing/>`_.
This policy assumes that there is a custom `User Field <https://meta.discourse.org/t/how-to-create-and-configure-custom-user-fields/113192>`_ in Discourse in position "1" that holds an UpHold or GateHub wallet payment pointer.
This policy also assumes that the Discourse server has the experimental `Metagov Web Monetization Discourse plugin <https://github.com/metagov/discourse-web-monetization>`_ installed, to generate revenue from forum content in the form of Web Monetization micropayments. All content generated on Discourse will be split equally between all wallets rev share config, which is stored in Metagov.

**Required integrations**: ``discourse``

**Filter:**

.. code-block:: python

    is_user_fields_changed = action.event_type == "discourse.user_fields_changed"
    if not is_user_fields_changed:
      return False

    user = action.data["username"]
    custom_wallet_field_key = "1"
    old_wallet = action.data.get("old_user_fields", {}).get(custom_wallet_field_key)
    new_wallet = action.data.get("user_fields", {}).get(custom_wallet_field_key)
    if old_wallet == new_wallet:
      logger.info(f"no wallet change for {user}, they must have changed another field. skipping.")
      return False

    logger.info(f"User {user} changed their wallet from '{old_wallet}' to '{new_wallet}'")
    proposal.data.set("old_wallet", old_wallet)
    proposal.data.set("new_wallet", new_wallet)
    return True

**Initialize:** ``pass``

**Notify:**

.. code-block:: python

    user = action.data["username"]

    old_wallet = proposal.data.get("old_wallet")
    new_wallet = proposal.data.get("new_wallet")
    if not new_wallet:
      logger.info("wallet was removed, no need to vote")
      return

    #get the current config
    response = metagov.perform_action("revshare.get-config", {})
    logger.info(f"get-config response: {response}")

    parameters = {
        "title": f"Add '{new_wallet}' to revshare config - test",
        "details": f"{user} proposes to add wallet '{new_wallet}' and remove wallet '{old_wallet or ''}'. The current revshare configuraton is: {response}",
       "options": ["approve", "disapprove"],
       "topic_id": 133
    }
    result = metagov.start_process("discourse.poll", parameters)
    poll_url = result.outcome.get("poll_url")
    logger.info(f"Vote at {poll_url}")


    params = {
        "title": f"Request to add '{new_wallet}' under review",
        "raw": f"Vote occurring at {poll_url}",
        "target_usernames": [user]
    }
    response = metagov.perform_action("discourse.create-message", params)
    proposal.data.set("dm_topic_id", response["topic_id"])





**Check:**

.. code-block:: python

    new_wallet = proposal.data.get("new_wallet")
    if not new_wallet:
      logger.info("wallet was removed, no need to vote")
      return PASSED


    result = metagov.get_process()
    if not result:
      return None

    logger.info(f"Discourse Poll ({result.status}) outcome: {result.outcome}")

    agrees = result.outcome.get("votes", {}).get("approve", 0)
    disagrees = result.outcome.get("votes", {}).get("disapprove", 0)

    if (agrees >= 1) or (disagrees >= 3):
      # custom closing condition was met, close the poll in Discourse
      metagov.close_process()
      return PASSED if agrees > disagrees else FAILED
    elif result.status == "completed":
      # the poll was "closed" on discourse by a user
      return PASSED if agrees > disagrees else FAILED

    return None # pending




**Pass:**

.. code-block:: python

     user = action.data["username"]
     old_wallet = proposal.data.get("old_wallet")
     new_wallet = proposal.data.get("new_wallet")

     logger.info(f"APPROVED: User {user} changed their wallet from '{old_wallet}' to '{new_wallet}'")

     # remove old pointer.
     if old_wallet:
       response = metagov.perform_action("revshare.remove-pointer", {"pointer": old_wallet})
       logger.info(f"remove-pointer response: {response}")

     if new_wallet:
       # add new pointer.
       response = metagov.perform_action("revshare.add-pointer", {"pointer": new_wallet, "weight": 1})
       logger.info(f"add-pointer response: {response}")


       params = {
           "raw": f"Your new payment pointer was added to the revshare config $$$! Current config is {response}",
           "target_usernames": [user],
           "topic_id": proposal.data.get("dm_topic_id")
       }
       metagov.perform_action("discourse.create-message", params)



**Fail:**

.. code-block:: python

    user = action.data["username"]
    old_wallet = proposal.data.get("old_wallet")
    new_wallet = proposal.data.get("new_wallet")

    logger.info(f"FAILED: User {user} changed their wallet from '{old_wallet}' to '{new_wallet}'")

    params = {
        "raw": f"Your request to get $$ was rejected",
        "target_usernames": [user],
       "topic_id": proposal.data.get("dm_topic_id")
    }
    metagov.perform_action("discourse.create-message", params)



