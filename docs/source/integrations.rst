.. _start:

Platform Integrations
====================================

| PolicyKit is an application that sits on its own server. However, it would be prohibitive if users of a social platform needed to go to PolicyKit for every governance task, such as proposing an action or voting on a proposal. In addition, as PolicyKit needs to enforce policies, it must have a way of stopping and allowing actions that are carried out on the platform itself, since the platform already has an existing governance that PolicyKit must supersede. These capabilities are defined in platform integration libraries that can be developed for any platform to connect with PolicyKit. Once a single developer has created an integration using a platform's web API, any community on that platform can use PolicyKit.


In order to install PolicyKit to a community, there must be an **authentication mechanism**, such as OAuth, for at least one admin or mod account to give access to PolicyKit so that it may govern a broad set of actions, including privileged ones.
In addition, each platform integration supports **one or more** of these capabilities:

* **Actions** are API requests to perform some action on a platform, such as sending a message to users. Some platforms don't require authentication (like SourceCred), others require API keys to be uploaded (Loomio, Open Collective) and others need to be authenticated via an OAuth flow (Slack, GitHub).
* **Trigger Actions** are platform events that can be used as policy triggers. Typically these are received via webhooks, so they may require registering a PolicyKit webhook URL for your community on the external platform. For platforms that don't support webhooks, some integrations have a polling mechanism to fetch data periodically and create triggers from new events.
* **Governable Actions** are a PolicyKit construct that combines "actions" and "trigger actions." A Governable Action can be reverted and re-executed, which allows PolicyKit to "govern" that capability on the platform. Policies that govern platform actions are called **Platform Policies** (see :doc:`Policy Examples <../policy_examples>`). This capability may require an admin account to give access to PolicyKit so that it may govern a broad set of actions, including privileged ones. All Governable Actions can also be used as triggers for Trigger Policies. 
* **Voting** is the ability to perform a vote on an external platform and capture the result.


..
   commented-out examples
    Example: ``slack.post_message(text="hello world", channel="ABC123")``, ``opencollective.process_expense(expense_id=123, action="REJECT")``, ``sourcecred.get_cred(username="user123")``

    Example: ``expensecreated``, ``slackrenameconverstion``
  
    Example: ``slackrenameconverstaion``
    
    Example: ``loomio.initiate_vote(title="please vote", closing_at=closing_at_dt, options=["consent", "objection", "abstain"])``



Once you have installed PolicyKit to one platform, you can enable additional integrations on the Settings page.
Only users with the ``Integration Admin`` role are able to add and remove integrations.

.. note::

  Some integrations require one-time setup process by a PolicyKit server admin. If you deploying your own instance of PolicyKit, see :doc:`Installation and Getting Started <gettingstarted>` for instructions. Platforms like Slack and Discord require an initial setup process to create bots/apps and store their Client IDs and secrets on the PolicyKit server.


Here is an overview of the capabilities supported by each platform integration:

Slack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The authentication mechanism for the Slack Integration is **OAuth**. The installing user must be an admin on Slack in order to install PolicyKit.

.. list-table:: 
   :widths: 25 5 70
   :header-rows: 0

   * - Actions
     - ✅
     - Write policies that perform actions on Slack, such as posting messages.
   * - Trigger Actions
     - ✅
     - Write Trigger Policies that are triggered by events that occurred on Slack (e.g. "when a Slack channel is renamed, update the generated welcome post")
   * - Governable Actions
     - ✅
     - Write Platform Policies that govern Slack actions (e.g. "only users with X role can rename Slack channels")
   * - Voting
     - ✅
     - Write policies that perform boolean- or single-choice voting in Slack channels or DMs.




Open Collective
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


The authentication mechanism for the Open Collective Integration is an **API Key** for a user with admin access to the collective. It also requires registering a webhook in Open Collective. Follow instructions on the setup page.

.. list-table:: 
   :widths: 25 5 70
   :header-rows: 0

   * - Actions
     - ✅
     - Write policies that perform actions on Open Collective, such as processing expenses or posting comments.
   * - Trigger Actions
     - ✅
     - Write Trigger Policies that are triggered by events that occurred on the Open Collective platform (e.g. "when an expense is created, start a vote on Slack")
   * - Governable Actions
     - ❌
     - 
   * - Voting
     - ❌
     - 


Loomio
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The authentication mechanism for the Loomio Integration is an **API Key**. It also requires registering a webhook in Loomio. Follow instructions on the setup page.

.. list-table:: 
   :widths: 25 5 70
   :header-rows: 0

   * - Actions
     - ❌
     - 
   * - Trigger Actions
     - ❌
     - 
   * - Governable Actions
     - ❌
     - 
   * - Voting
     - ✅
     - Write policies that perform votes on Loomio.


GitHub
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The authentication mechanism for the GitHub Integration is **OAuth**.

.. list-table:: 
   :widths: 25 5 70
   :header-rows: 0

   * - Actions
     - ❌
     - 
   * - Trigger Actions
     - ✅
     - Write Trigger Policies that are triggered by events that occurred on GitHub (e.g. "when a new issue is created, post about it on Slack if certain conditions are met").
   * - Governable Actions
     - ❌
     - 
   * - Voting
     - ✅
     - Write policies that perform votes on Github.


SourceCred
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There is no authentication mechanism for the SourceCred Integration. The SourceCred server must be public. The only thing this integration supports is fetching cred and grain values.

.. list-table:: 
   :widths: 25 5 70
   :header-rows: 0

   * - Actions
     - ✅
     - Write policies that fetch SourceCred values from the configured SourceCred instance.
   * - Trigger Actions
     - ❌
     - 
   * - Governable Actions
     - ❌
     - 
   * - Voting
     - ❌
     - 

Reddit
~~~~~~

.. list-table:: 
   :widths: 25 5 70
   :header-rows: 0

   * - Actions
     - ✅
     - Write policies that perform actions on Reddit, such as posting messages.
   * - Trigger Actions
     - ✅
     - Write Trigger Policies that are triggered by events that occurred on Reddit.
   * - Governable Actions
     - ✅
     - Write Platform Policies that govern Reddit posting
   * - Voting
     - ✅
     - Write policies that perform boolean voting on a Reddit thread


Discord
~~~~~~~

The authentication mechanism for the Discord Integration is **OAuth**. The installing user must be an admin on Discord in order to install PolicyKit.

.. list-table:: 
   :widths: 25 5 70
   :header-rows: 0

   * - Actions
     - ✅
     - Write policies that perform actions on Discord, such as posting messages.
   * - Trigger Actions
     - ✅
     - The only supported trigger action currently is DiscordSlashCommand. (e.g. "when a user invokes the policykit bot with "/policykit whatever", do something)
   * - Governable Actions
     - ❌
     - 
   * - Voting
     - ✅
     - Write policies that perform boolean- or single-choice voting in a Discord channel.



Discourse
~~~~~~~~~

The authentication mechanism for the Discourse Integration is **OAuth**. This integration requires a Discourse admin to do some setup steps in Discourse before PolicyKit can be installed.

.. list-table:: 
   :widths: 25 5 70
   :header-rows: 0

   * - Actions
     - ✅
     - Write policies that create posts and topics on Discourse.
   * - Trigger Actions
     - ✅
     - Write Trigger Policies that are triggered by events that occurred on Discourse (e.g. "when a user posts a new topic in a certain category, do something)
   * - Governable Actions
     - ✅
     - Write Platform Policies that govern Discourse actions (e.g. "only users with X amount of Cred can post on this Discourse topic")
   * - Voting
     - ❌
     - 



Setting up your Discourse community
"""""""""""""""""""""""""""""""""""


You can set up a Discourse community either by running a server that hosts a community locally or by creating a community hosted remotely by `Discourse.org <https://www.discourse.org/>`_. To host a community remotely, you can press "Start Trial" `on this page <https://www.discourse.org/pricing>`_ and follow the instructions to set up a community. Discourse.org offers free 14 day trials, which can be extended by contacting support.

Once the site is up and running, you need to configure a few settings to enable PolicyKit to interact with your site. On the site homepage, log in as your admin account and enter the Settings menu (located on the top right of the homepage). On the left sidebar, select the User API page. On this page, you should set / verify the following settings:

 * **allow user api keys**: ``checked``
 * **allow user api key scopes**: Select the scopes you want to enable here. Possible scopes: ``read``, ``write``, ``message_bus``, ``push``, ``notifications``, ``session_info``, ``one_time_password``. Recommend allowing all the scopes for full usability of PolicyKit.
 * **min user level for user api key**: ``0``
 * **allowed user api auth redirects**: Add an entry: ``[POLICYKIT_URL]/discourse/auth``. (example: ``https://policykit.org/discourse/auth``)

Installing PolicyKit to your Discourse community
"""""""""""""""""""""""""""""""""""""""""""""""""

On the login page, select "Install PolicyKit to Discourse". On the Configure screen that appears, enter the full URL of your Discourse community (example: ``https://policykit.trydiscourse.com``). On the next screen that appears, you must approve PolicyKit's authorization to access your Discourse community. On the third and final screen, you must select a Starter Kit system of governance, which will initialize your community with the selected system of governance.

For testing purposes, we recommend trying out the Testing Starter Kit, which will give all members in the community complete access to PolicyKit action. For more experienced PolicyKit users who are hoping to use PolicyKit with an existing community, we recommend trying out one of the other more restrictive Starter Kits.

Once you have selected a Starter Kit, you will be redirected back to the login page. If PolicyKit was installed correctly, you should see a text message near the top saying "Successfully added PolicyKit!". If you see this success message, you are all set to sign in to your Discourse community's dashboard.

Signing in to your PolicyKit dashboard
""""""""""""""""""""""""""""""""""""""""""

On the login page, select "Sign in with Discourse". This will display a screen asking "Which Discourse community would you like to sign into?" In the text box, enter the full URL of your Discourse community (example: ``https://policykit.trydiscourse.com``) and press Continue. Once again, you must approve PolicyKit's authorization to access your Discourse community. After approving the request, you should be in! You should now be able to see your PolicyKit dashboard and use all the features of PolicyKit with your Discourse community.

Metagov (experimental)
~~~~~~~~~~~~~~~~~~~~~~~~~

PolicyKit uses `Metagov <http://docs.metagov.org/>`_ to integrate with and and govern a range of external platforms.
PolicyKit exposes some generic tools to interact with any available Metagov plugins.
These are experimental and typically would only be used if you are developing a new Metagov Plugin that doesn't yet have a PolicyKit integration.

Webhook Trigger Action
"""""""""""""""""""""""""""""""""

All events received from Metagov generate a generic trigger action. To write a policy triggered by this generic action, select ``Webhook Trigger Action`` in the action types dropdown.
Use the ``filter`` block to choose which event type your policy is triggered by. The event type is stored at ``action.event_type``, and any additional data is stored as a dict at ``action.data``.

.. code-block:: python

    # "filter" block

    return action.event_type == 'opencollective.expense_created'

Performing actions
""""""""""""""""""""""""""

Platform policies have access to a ``metagov`` client that can be used to perform actions that are defined on a Metagov Plugin.
Policy authors can only use actions that are defined in Plugins that are currently enabled in their community.

.. code-block:: python

    # "check" block

    parameters = {"low": 0, "high": 10}
    response = metagov.perform_action("randomness.random-int", parameters)
    if response and response.get('value') >  5:
        return PASSED
    else:
        return FAILED


Performing governance processes
"""""""""""""""""""""""""""""""""""""""

Platform policies can use the ``metagov`` client to perform asynchronous governance processes.
Here's a partial example of a policy that uses the ``loomio.poll`` process to perform a vote.

.. code-block:: python

    # "notify" block kicks off the process

    import datetime

    closing_at = (action.proposal.proposal_time + datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    result = metagov.start_process("loomio.poll", {
        "title": "Agree or disagree?",
        "options": ["agree", "disagree"],
        "closing_at": closing_at
    })
    poll_url = result.get('poll_url')


.. code-block:: python

    # "check" block polls for the process outcome

    result = metagov.get_process()
    if result.status != "completed":
        return # still processing
    if result.errors:
        return FAILED
    if result.outcome:
        agree_count = result.outcome.get("agree")
        disagree_count = result.outcome.get("disagree")
        return PASSED if agree_count > disagree_count else FAILED
    return FAILED
