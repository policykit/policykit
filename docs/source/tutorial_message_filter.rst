.. _start:

Tutorial 1: Message Filter
--------------------------

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

We only want our Message Filter policy to run on actions which are messages posted to the Discord channel we are monitoring. To check if the action is a posted message, we can check a property of the ``action`` object called ``action_codename``. The codename for posting a message on Discord is ``"discordpostmessage"``. Thus, our Filter block is::

  if action.action_codename == "discordpostmessage":
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
