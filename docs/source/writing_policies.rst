.. _start:

Writing Policies
====================================


Once any new action is proposed by a user, either by invoking it on the PolicyKit website or on a particular community platform, it passes through the Policy engine evaluation loop.
It may be helpful to review the :ref:`Policy Engine Evaluation Loop` to understand how policy evaluations are triggered.


Policy code is divided into 5 discrete blocks: ``filter``, ``initialize``, ``check``, ``notify``, ``pass``, and ``fail``.
Scope is not shared across blocks.
See the :doc:`Evaluation Context <api_context>` reference for what's in scope to the policy author in each block.


See :doc:`Policy Examples <policy_examples>` for example policies that can be downloaded and uploaded into your PolicyKit community.

Action Types
""""""""""""""

This function specifies the scope of the policy.
For Platform Policies and Constitution Policies, the action type indicates which action type the policy governs.
For Trigger Policies, the action type indicates which action types trigger the policy to evaluate. When a Policy is evaluated against an Action, a ``Proposal`` record is created to store any data relevant to the policy evaluation.


Each community is set up with a **Starter Kit** which defines the **Base Policies** for governing platform and constitution actions. Base policies act as a "fallback policy" and applies to ALL action types. Base policies are overridden by creating more specific Platform and Constitution policies.


Filter
""""""""

This function allows the policy author to further filter down the scope of the policy. The function returns ``True`` if the policy governs the action object passed in as an argument. For instance, if the policy is meant to cover only one type of action, the function can check the ``action_type`` field of the action object. The policy could also filter on the initiator of the action or even the time of day, if, for example, the community has decided that Friday evenings are a free-for-all in a particular channel.

Initialize
""""""""""""""

If ``filter`` returns true, the action in question is considered in scope for this policy, and we move on to ``initialize``. Within this function, the author can specify any code that must be completed once at the start of the policy to set it up.

Check
""""""""""""""

This block should return ``PROPOSED``, ``PASSED``, or ``FAILED``.


The ``check`` function specifies the conditions that need to be met so that an action has passed or failed. For example, it may test whether a vote has reached a quorum, or whether an elected individual has responded to the proposal. When created, all actions have a status of ``PROPOSED``. New actions first encounter ``check`` immediately after ``initialize``; this is so that in case the policy can already pass or fail, we can exit the workflow early. For instance, if there was a policy that holds messages containing profanity for review by a moderator, the policy would automatically pass actions that do not contain profanity.


As long as an action is still ``PROPOSED``, ``check`` will run periodically until it returns ``PASSED`` or ``FAILED``. If ``check`` does not return anything, ``PROPOSED`` is presumed. For instance, if a policy calls for a vote from users, it may take time for the required number of votes to come in. The policy's ``check`` function could also specify a maximum amount of time, at which point the action fails.

Notify
""""""""""""""

If the policy involves reaching out to one or more community members for input, then the code for notifying members occurs in this function.
While policy authors can send messages to users in any function, this function is specifically for notifications soliciting user input.
Authors may use the method ``initiate_vote`` to start a vote on whether or not to pass the action.
This function is only run once, after a new action does not return ``PASSED`` or ``FAILED`` from the first ``check``, so as to not unnecessarily notify users.

Pass
""""""""""""""

This function runs if an action is passed (e.g. ``check`` returned ``PASSED``).
Code that could go here includes: post-action clean-up tasks such as announcing the outcome to the voters or to the community.

When a Governable Action is passed, the engine automatically executes it, if applicable (see evaluation loop diagram).

Fail
""""""""""""""

This function runs if the action fails to pass the policy (e.g. ``check`` returned ``FAILED``).
Code that could go here includes: invoking fall-back actions due to failure, or share the outcome privately with the proposer alongside an explanation of why the action failed.

When a Governable Action is failed, the engine automatically executes it, if applicable (see evaluation loop diagram).