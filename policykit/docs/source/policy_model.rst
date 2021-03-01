.. _start:

The Policy Model
====================================

| Once any new action is proposed by a user, either by invoking it on the PolicyKit website or on a particular community platform, it passes through the PolicyEngine workflow, first calling the filter()function for each policy. All functions are passed the action object that is being evaluated and the policy object of the function.

Filter
~~~~~~~~~~~~~~~~~~~~~~~~

| This function specifies the scope of the policy, or what types of actions the policy governs. The function returns ``True`` if the policy governs the action object passed in as an argument. For instance, if the policy is meant to cover only one type of action, the function can check the ``action_type`` field of the action object. The policy could also filter on the initiator of the action or even the time of day, if, for example, the community has decided that Friday evenings are a free-for-all in a particular channel.

Initialize
~~~~~~~~~~~~~~~~~~~~~~~~

| If ``filter()`` returns true, the action in question is considered in scope for this policy, and we move on to ``initialize()``. Within this function, the author can specify any code that must be completed once at the start of the policy to set it up. For instance, in the jury example, ``initialize()`` selects the random jury who will decide on the action.

Check
~~~~~~~~~~~~~~~~~~~~~~~~

| The ``check()`` function specifies the conditions that need to be met so that an action has passed or failed. For example, it may test whether a vote has reached a quorum, or whether an elected individual has responded to the proposal. When created, all actions have a status of ``PROPOSED``. New actions first encounter ``check()`` immediately after ``initialize()``; this is so that in case the policy can already pass or fail, we can exit the workflow early. For instance, if there was a policy that holds messages containing profanity for review by a moderator, the policy would automatically pass actions that do not contain profanity. As long as an action is still ``PROPOSED``, ``check()`` will run periodically until it returns ``PASSED`` or ``FAILED``. If ``check()`` does not return anything, ``PROPOSED`` is presumed. For instance, if a policy calls for a vote from users, it may take time for the required number of votes to come in. The policy's ``check()`` function could also specify a maximum amount of time, at which point the action fails.

Notify
~~~~~~~~~~~~~~~~~~~~~~~~

| If the policy involves reaching out to one or more community members for input, then the code for notifying members occurs in this function. While policy authors can send messages to users in any function, this function is specifically for notifications soliciting user input. Authors may use the helper method ``notify\_action()`` to send messages to community members, with ability to customize the post. For instance, the notification post can include instructions, such as to deliberate the action before voting. This function is only run once, after a new action does not return ``PASSED`` or ``FAILED`` from the first ``check()``, so as to not unnecessarily notify users.

Pass
~~~~~~~~~~~~~~~~~~~~~~~~

| This function runs if an action is passed. Each action class implements an ``execute()`` method that policy authors can call to carry out the action. Other code that could go here include post-action clean-up tasks such as announcing the outcome to the voters or to the community.

Fail
~~~~~~~~~~~~~~~~~~~~~~~~

| This function runs if the action fails to pass the policy. For instance, the author could add code to invoke fall-back actions due to failure, or share the outcome privately with the proposer alongside an explanation of why the action failed.
