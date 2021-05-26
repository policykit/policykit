.. _start:

Integrations
====================================

| PolicyKit is an application that sits on its own server. However, it would be prohibitive if users of a social platform needed to go to PolicyKit for every governance task, such as proposing an action or voting on a proposal. In addition, as PolicyKit needs to enforce policies, it must have a way of stopping and allowing actions that are carried out on the platform itself, since the platform already has an existing governance that PolicyKit must supersede. These capabilities are defined in platform integration libraries that can be developed for any platform to connect with PolicyKit. Once a single developer has created an integration using a platform's web API, any community on that platform can use PolicyKit.

| In order to install PolicyKit to a community, there must be an **authentication workflow**, such as OAuth, for at least one admin or mod account to give access to PolicyKit so that it may govern a broad set of actions, including privileged ones. The platform integration must also specify ways to **send messages** to users on the platform. In order for PolicyKit to govern actions, it must know what **platform actions** are possible; these are specified via the creation of ``PlatformAction`` classes. Actions typically are carried out via web API endpoints provided by the platform that are then made available through an ``execute()`` method in the action class and undoable via a ``revert()`` method. Finally, the integration must incorporate a **listener** to listen for user actions on the platform as well as a listener for votes on a notification message. For instance, votes could be recorded via an emoji reaction or a reply to a notification message.

| So far, we have implemented platform integrations for the platforms Slack, Reddit, Discord and Discourse.

Slack Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Initial Slack Setup
"""""""""""""""""""
The PolicyKit server admin needs to do this once. After this is complete, your PolicyKit instance can be installed to any number of Slack servers.

1. Go to https://api.slack.com/apps
2. Click "Create New App" to create your PolicyKit application
3. Click "Event Subscriptions"->"Enable Events" and enter the request URL ``[POLICYKIT_URL]/slack/action``. Subscribe to bot events and subscribe to events on behalf of users.
4. Click "OAuth & Permissions" and add redirect URL ``[POLICYKIT_URL]/slack/oauth``
5. Click "Manage Distribution"->"Activate Public Distribution"
6. Click "Basic Information." Copy the Client ID and Client Secret into the ``private.py`` file on your PolicyKit server.
7. Reload apache2: ``systemctl reload apache2``
8. To test it out, open ``[POLICYKIT_URL]/main`` and click "Add to Slack."
9. Now, you should be able to use "Sign in with Slack" to access the PolicyKit dashboard for the community you just installed PolicyKit to.


Discord Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Initial Discord Setup
"""""""""""""""""""""

The PolicyKit server admin needs to do this once. After this is complete, your PolicyKit instance can be installed to any number of Discord servers.

1. Go to https://discord.com/developers/applications
2. Click "New Application" to create your PolicyKit application
3. Under OAuth2, add the redirect URL ``[POLICYKIT_URL]/discord/oauth``
4. Add a new Bot and enable these options:

    - Public Bot
    - Requires OAuth2 Code Grant
    - Presence Intent
    - Server Members Intent

5. Copy the bot token into ``DISCORD_BOT_TOKEN`` in ``private.py`` file on your PolicyKit server.
6. On the OAuth2 page, get the Client ID and Client Secret and copy them into ``private.py``.
7. Reload apache2: ``systemctl reload apache2``
8. To test it out, open ``[POLICYKIT_URL]/main`` and click "Install PolicyKit to Discord."
9. Now, you should be able to use "Sign in with Discord" to access the PolicyKit dashboard for the community you just installed PolicyKit to.


Discourse Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a connector for `Discourse <https://www.discourse.org/>`_ that lets you write policies that govern Discourse communities.

Initial Discourse Setup
"""""""""""""""""""""""

There is no initial setup required for Discourse. However, each Discourse community that installs PolicyKit will need to register the auth redirect separately (see below).


Setting up your Discourse community
"""""""""""""""""""""""""""""""""""


You can set up a Discourse community either by running a server that hosts a community locally or by creating a community hosted remotely by `Discourse.org <https://www.discourse.org/>`_. To host a community remotely, you can press "Start Trial" `on this page <https://www.discourse.org/pricing>`_ and follow the instructions to set up a community. Discourse.org offers free 14 day trials, which can be extended by contacting support.

|

Once the site is up and running, you need to configure a few settings to enable PolicyKit to interact with your site. On the site homepage, log in as your admin account and enter the Settings menu (located on the top right of the homepage). On the left sidebar, select the User API page. On this page, you should set / verify the following settings:

 * **allow user api keys**: ``checked``
 * **allow user api key scopes**: Select the scopes you want to enable here. Possible scopes: ``read``, ``write``, ``message_bus``, ``push``, ``notifications``, ``session_info``, ``one_time_password``. Recommend allowing all the scopes for full usability of PolicyKit.
 * **min user level for user api key**: ``0``
 * **allowed user api auth redirects**: Add an entry: ``[POLICYKIT_URL]/discourse/auth``. (example: ``https://policykit.org/discourse/auth``)

 Installing PolicyKit to your Discourse community
"""""""""""""""""""""""""""""""""""""""""""""""""

On the login page, select "Install PolicyKit to Discourse". On the Configure screen that appears, enter the full URL of your Discourse community (example: ``https://policykit.trydiscourse.com``). On the next screen that appears, you must approve PolicyKit's authorization to access your Discourse community. On the third and final screen, you must select a Starter Kit system of governance, which will initialize your community with the selected system of governance.

|

For testing purposes, we recommend trying out the Testing Starter Kit, which will give all members in the community complete access to PolicyKit action. For more experienced PolicyKit users who are hoping to use PolicyKit with an existing community, we recommend trying out one of the other more restrictive Starter Kits.

Once you have selected a Starter Kit, you will be redirected back to the login page. If PolicyKit was installed correctly, you should see a text message near the top saying "Successfully added PolicyKit!". If you see this success message, you are all set to sign in to your Discourse community's dashboard.

Signing in to your PolicyKit dashboard
""""""""""""""""""""""""""""""""""""""""""

On the login page, select "Sign in with Discourse". This will display a screen asking "Which Discourse community would you like to sign into?" In the text box, enter the full URL of your Discourse community (example: ``https://policykit.trydiscourse.com``) and press Continue. Once again, you must approve PolicyKit's authorization to access your Discourse community. After approving the request, you should be in! You should now be able to see your PolicyKit dashboard and use all the features of PolicyKit with your Discourse community.

Reddit Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Reddit integration is not yet documented.

Metagov Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a special connector for `Metagov <http://docs.metagov.org/>`_ that lets you write policies that make use of the `Metagov API <https://prototype.metagov.org/redoc/>`_, which provides access to several external platforms and governance tools.

Initial Setup
"""""""""""""

To use Metagov with PolicyKit, the server admin needs to do this once:

1. Deploy an instance of Metagov on the same machine as PolicyKit. See `Installing Metagov <https://docs.metagov.org/en/latest/installation.html>`_ for instructions.
2. In the ``.env`` file in Metagov, set the URL for receiving events: ``DRIVER_EVENT_RECEIVER_URL=[POLICYKIT_URL]/metagov/internal/action``
3. To enable Metagov in PolicyKit, set the ``METAGOV_URL`` in your ``private.py`` file to point to your Metagov instance.
4. Ensure that ``/metagov/internal`` is restricted to local traffic. Follow the Apache2 example in :doc:`Getting Started <../gettingstarted>`.


Configuring Metagov
"""""""""""""""""""

Configure Metagov by navigating to "Settings" in the PolicyKit web interface.
Only the users with role ``Metagov Admin`` are permitted to view and edit the Metagov configuration.
Use the editor to enable/disable plugins and to configure them.

Metagov events as policy triggers
"""""""""""""""""""""""""""""""""

Platform policies can be "triggered" by events that are emmitted by `Metagov listener <https://docs.metagov.org/en/latest/plugin_tutorial.html#listener>`_.
Use the ``filter`` block to determine whether the event is coming from Metagov. The ``action`` will be an instance of ``MetagovPlatformAction``:

.. code-block:: python

    # "filter" block

    return action.action_codename == 'metagovaction' \
        and action.event_type == 'opencollective.expense_created'

    # special properties on MetagovPlatformAction:
    action.event_data                                # dict: data about the event
    action.initiator.metagovuser.external_username   # str: username on the external platform

Metagov actions
""""""""""""""""""""""""""

Platform policies have access to a ``metagov`` client that can be used to invoke Metagov ``/action`` and ``/process`` endpoints.
Refer to the `Metagov API docs <https://prototype.metagov.org/redoc/>`_ to see which actions and processes are available to you.
Policy authors can only use actions that are defined in plugins that are *currently enabled* in their community.
See the :doc:`Sample Policies <../sample_policies>` for more examples.

.. code-block:: python

    # "check" block

    parameters = {"low": 0, "high": 10}
    response = metagov.perform_action("randomness.random-int", parameters)
    if response and response.get('value') >  5:
        return PASSED
    else:
        return FAILED


Metagov governance processes
""""""""""""""""""""""""""""

Platform policies can use the ``metagov`` client to perform asynchronous governance processes.
Here's a partial example of a policy that uses the ``loomio.poll`` process to perform a vote.
See the :doc:`Sample Policies <../sample_policies>` for more examples.

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
