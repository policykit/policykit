.. _start:

Integrations
====================================

| PolicyKit is an application that sits on its own server. However, it would be prohibitive if users of a social platform needed to go to PolicyKit for every governance task, such as proposing an action or voting on a proposal. In addition, as PolicyKit needs to enforce policies, it must have a way of stopping and allowing actions that are carried out on the platform itself, since the platform already has an existing governance that PolicyKit must supersede. These capabilities are defined in platform integration libraries that can be developed for any platform to connect with PolicyKit. Once a single developer has created an integration using a platform's web API, any community on that platform can use PolicyKit.

| In order to install PolicyKit to a community, there must be an **authentication workflow**, such as OAuth, for at least one admin or mod account to give access to PolicyKit so that it may govern a broad set of actions, including privileged ones. The platform integration must also specify ways to **send messages** to users on the platform. In order for PolicyKit to govern actions, it must know what **platform actions** are possible; these are specified via the creation of ``PlatformAction`` classes. Actions typically are carried out via web API endpoints provided by the platform that are then made available through an ``execute()`` method in the action class and undoable via a ``revert()`` method. Finally, the integration must incorporate a **listener** to listen for user actions on the platform as well as a listener for votes on a notification message. For instance, votes could be recorded via an emoji reaction or a reply to a notification message.

| So far, we have implemented platform integrations for the platforms Slack, Reddit, Discord and Discourse.

Slack Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Reddit Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Discord Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Discourse Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Metagov Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This is a special connector for `Metagov <http://docs.metagov.org/>`_ that lets you write policies that make use of the `Metagov API <https://prototype.metagov.org/redoc/>`_, which provides access to several external platforms and governance tools.
In order to use this integration, you need to deploy an instance of Metagov on the same machine as PolicyKit.

Configuring Metagov
"""""""""""""""""""

Configure Metagov by navigating to ``/metagov/config`` in the browser for your policykit instance. Only administrators are able to see this screen.
Use the screen to input the plugin configurations for any Metagov plugins you wish to enable. For example:

.. code-block:: json

    {
        "name": "<set by PolicyKit>",
        "readable_name": "<set by PolicyKit>",
        "plugins": [
            {
                "name": "sourcecred",
                "config": {
                    "server_url": "<sourcecred server URL>"
                }
            },
            {
                "name": "discourse",
                "config": {
                    "server_url": "<discourse server URL>",
                    "api_key": "<discourse api key>",
                    "webhook_secret": "<discourse webhook secret>"
                }
            },
            {
                "name": "opencollective",
                "config": {
                    "api_key": "<opencollective api key>",
                    "collective_slug": "<opencollective slug>",
                    "webhook_slug": "<opencollective webhook slug>"
                }
            },
            {
                "name": "loomio",
                "config": {
                    "api_key": "<loomio api key>"
                }
            }
        ]
    }

Metagov events as policy triggers
"""""""""""""""""""""""""""""""""

If you want to write a policy that is "triggered" by an event emitted by a `Metagov listener <https://docs.metagov.org/en/latest/plugin_tutorial.html#listener>`_,
you can use the ``fitler`` block. The ``action`` will be an instance of ``MetagovPlatformAction``.

.. code-block:: python

    # "filter" block

    return action.action_codename == 'metagovaction' \
        and action.event_type == 'opencollective.expense_created'

    # special properties on MetagovPlatformAction:
    action.event_data                                # dict: data about the event
    action.initiator.metagovuser.external_username   # str: username on the external platform

Metagov actions
""""""""""""""""""""""""""

Policy authors have access to a ``metagov`` client that can be used to invoke Metagov ``/action`` and ``/process`` endpoints.
Refer to the `Metagov API docs <https://prototype.metagov.org/redoc/>`_ to see which actions and processes are available to you.
Policy authors can only use actions that are defined in **plugins that are currently enabled in their community**.

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

Use the ``metagov`` client to perform asynchronous governance processes. Here's a partial example of a policy that uses the ``loomio.poll`` process to perform a vote.

.. code-block:: python

    # "notify" block kicks off the process
    
    import datetime

    closing_at = action.proposal.proposal_time + datetime.timedelta(days=3)
    result = metagov.start_process("loomio.poll", {
        "title": "Agree or disagree?",
        "options": ["agree", "disagree"],
        "closing_at": closing_at.strftime("%Y-%m-%d")
    })
    poll_url = result.get('poll_url')
    # elided: send the poll URL to users and let them know to vote


.. code-block:: python

    # "check" block polls for the process outcome
    
    result = metagov.get_process_outcome()
    if result is None:
        return # still processing
    if result.errors:
        return FAILED
    if result.outcome:
        agree_count = result.outcome.get("agree")
        disagree_count = result.outcome.get("disagree")
        return PASSED if agree_count > disagree_count else FAILED
    return FAILED
