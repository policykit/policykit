.. _start:


Policy Examples
###############

This is a library of example policies to get started.


.. include:: generated_policy_examples.inc


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

