.. _start:

Installation and Getting Started
====================================

| On this page, we will take you through the process of setting up PolicyKit, both for local development and on an Ubuntu server.

Getting Started
---------------

| PolicyKit requires Python 3. Before you install, we recommend that you activate a Python 3+ virtual environment.

| To begin, clone the `PolicyKit GitHub repository <https://github.com/amyxzhang/policykit>`_ (or your fork) and navigate to the python project root:

::

 git clone https://github.com/amyxzhang/policykit.git
 cd policykit/policykit

| From here, run the following commands to install PolicyKit's dependencies:

::

 pip install --upgrade pip
 pip install -r requirements.txt

| Next, run the following command to create a file to store your API keys:

::

 cp private_template.py private.py

| PolicyKit requires a file to log to. By default, it logs to the file ``/var/log/django/debug.log``. To change this, set the ``POLICYKIT_LOG_FILE`` environment variable or edit the ``LOGGING`` object in ``settings.py`` directly.

| To verify that you have set the PolicyKit server up correctly, run the following command:

::

 python manage.py runserver

| To use PolicyKit, you must set up your own database. You can use the default ``sqlite`` or ``mysql`` or another database of your choice. Edit the ``DATABASES`` field in ``settings.py`` to point to the right database. Django will create the database as long as the parent directory exists.

| Run the following command to create and set up the database:

::

 python manage.py migrate

| Finally, you need to set up PolicyKit's governance starter kits. Run the following command to enter the shell:

::

 python manage.py shell_plus

From the shell prompt, run the following command to create the starterkits:

::

 exec(open('scripts/starterkits.py').read())

Open PolicyKit in the browser at http://localhost:8000/main


Running PolicyKit on a Server
-----------------------------

| Thus far, we have been run in Ubuntu 18.04 and Ubuntu 20.04, and the below instructions should work for both.

1. Add PolicyKit to the server by uploading the codebase or using ``git clone``.
2. Follow `this guide <https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-programming-environment-on-an-ubuntu-20-04-server>`_ to install Python3 and to create a virtual environment for PolicyKit.
3. Install the requirements to the virtual environment with ``pip install -r requirements.txt``.
4. Finish the earlier guide to setting up PolicyKit.
5. Make the following additional changes to ``private.py``:

   - Set the ``SERVER_URL`` field
   - You can leave the platform integration API keys/secrets empty for now. Follow the instructions under "Set up Integrations" to set up each integration.

6. Make the following additional changes to ``policykit/settings.py``:

   - Update the ``ALLOWED_HOSTS`` field to point to your host.

   - Update that the database path under ``DATABASES``. Recommended: set the database path to ``/var/databases/policykit/db.sqlite3``. Make sure the directory exists.

   - Set ``DEBUG`` to False

   - Set ``SECRET_KEY`` to a new Django secret key. Generate a key with this command:

           .. code-block::

                   python manage.py shell -c 'from django.core.management import utils; print(utils.get_random_secret_key())'

7. Next, run the following command to collect static files into a ``static/`` folder:

::

 python manage.py collectstatic


Deploy with Apache web server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now that you have PolicyKit installed on your server, you can deploy it on Apache web server.
Make sure you have a domain dedicated to Policykit that is pointing to your server's IP address.

.. note::

        In the remaining examples, make sure to substitute the following values:

        ``$POLICYKIT_REPO`` is the path to your policykit repository root. (``/policykit``)

        ``$POLICYKIT_ENV`` is the path to your policykit virtual environment. (``/environments/policykit_env``)

        ``$SERVER_NAME`` is  your server name. (``policykit.mysite.com``)

1. Install apache2

   .. code-block:: shell

        sudo apt-get install apache2 libapache2-mod-wsgi-py3

2. Create a new apache2 config file:

   .. code-block:: shell

        cd /etc/apache2/sites-available
        # replace SERVER_NAME (ie policykit.mysite.com.conf)
        cp default-ssl.conf SERVER_NAME.conf

3. Edit the config file to look like this:


   .. code-block:: aconf

        <IfModule mod_ssl.c>
                <VirtualHost _default_:443>
                        ServerName $SERVER_NAME
                        ServerAdmin webmaster@localhost
                        Alias /static $POLICYKIT_REPO/policykit/static

                        <Directory $POLICYKIT_REPO/policykit/static>
                                Require all granted
                        </Directory>

                        # Grant access to wsgi.py file. This is the Django server.
                        <Directory $POLICYKIT_REPO/policykit/policykit>
                                <Files wsgi.py>
                                        Require all granted
                                </Files>
                        </Directory>

                        # 🚨 IMPORTANT: Restrict internal endpoints to local traffic 🚨
                        <Location /metagov/internal>
                                Require ip YOUR-IP-ADDRESS
                        </Location>

                        WSGIDaemonProcess policykit python-home=$POLICYKIT_ENV python-path=$POLICYKIT_REPO/policykit
                        WSGIProcessGroup policykit
                        WSGIScriptAlias / $POLICYKIT_REPO/policykit/policykit/wsgi.py
                        # .. REST ELIDED
                </VirtualHost>
        </IfModule>

4. Test your config with ``apache2ctl configtest``. You should get a "Syntax OK" as a response. 

5. Enable your site:

        .. code-block:: shell

                # activate your config
                a2ensite /etc/apache2/sites-available/$SERVER_NAME.conf

                # disable the default config
                sudo a2dissite 000-default-le-ssl.conf

6. Get an SSL certificate and set it up to auto-renew using LetsEncrypt:

    .. code-block:: shell

        sudo apt install certbot python3-certbot-apache
        sudo certbot --apache

7. Add the certificates to your ``$SERVER_NAME.conf`` file:

    .. code-block:: aconf

        SSLCertificateFile /etc/letsencrypt/live/$SERVER_NAME/fullchain.pem
        SSLCertificateKeyFile /etc/letsencrypt/live/$SERVER_NAME/privkey.pem

8. Reload the config:

     .. code-block:: shell

          systemctl reload apache2


9.  Give the Apache2 user access to the database directory and the logging directory (update paths as needed):

        .. code-block:: shell

                sudo chown -R www-data:www-data /var/log/django
                sudo chown -R www-data:www-data /var/databases/policykit

10. Load your site in the browser and navigate to ``/login``. You should see a site titled "Django adminstration" with options to connect to Slack, Reddit, Discourse, and Discord. Before you can install PolicyKit into any of these platforms, you'll need to set the necessary client IDs and client in ``private.py``. Follow the setup instructions for each integration in :doc:`Integrations <../integrations>`.

  Check for errors at ``/var/log/apache2/error.log`` and ``/var/log/django/debug.log`` (or whatever logging path you have defined in ``settings.py``).

11. Any time you update the code, you'll need to run ``systemctl reload apache2`` to reload the server.

Set up Celery
^^^^^^^^^^^^^

PolicyKit uses `Celery <https://docs.celeryproject.org/en/stable/index.html>`_ to run scheduled tasks.
Follow these instructions to run a celery daemon on your Ubuntu machine using ``systemd``.
For more information about configuration options, see the `Celery Daemonization <https://docs.celeryproject.org/en/stable/userguide/daemonizing.html>`_.

.. note::

        Using PolicyKit with Metagov? These configuration files are designed specifically to work with the setup where PolicyKit and Metagov are deployed together.
        PolicyKit and Metagov will use separate celery daemons that use separate RabbitMQ virtual hosts, configured using ``CELERY_BROKER_URL``.


Create RabbitMQ virtual host
""""""""""""""""""""""""""""

Install RabbitMQ and create a virtual host:

.. code-block:: shell

    sudo apt-get install rabbitmq-server

    sudo rabbitmqctl add_user 'username' 'password'
    sudo rabbitmqctl add_vhost 'policykit-vhost'
    sudo rabbitmqctl set_permissions -p 'policykit-vhost' 'username' '.*' '.*' '.*'

In ``policykit/settings.py``, set the ``CELERY_BROKER_URL`` as follows, substituting values for your RabbitMQ username, password, and virtual host:

.. code-block:: python

    CELERY_BROKER_URL = "amqp://USERNAME:PASSWORD@localhost:5672/CUSTOMVIRTUALHOST"

Create celery user
""""""""""""""""""

If you don't already have a ``celery`` user, create one:

.. code-block:: bash

        sudo useradd celery -d /home/celery -b /bin/bash

Give the ``celery`` user access to necessary pid and log folders:

.. code-block:: bash

        sudo useradd celery -d /home/celery -b /bin/bash
        sudo mkdir /var/log/celery
        sudo chown -R celery:celery /var/log/celery
        sudo chmod -R 755 /var/log/celery

        sudo mkdir /var/run/celery
        sudo chown -R celery:celery /var/run/celery
        sudo chmod -R 755 /var/run/celery

The ``celery`` user will also need write access to the Django log file and the database.
To give ``celery`` access, create a group that contains both ``www-data`` (the apache2 user) and ``celery``.
For example, if your Django logs are in ``/var/log/django`` and your database is in ``/var/databases``:

.. code-block:: bash

        sudo groupadd www-and-celery
        sudo usermod -a -G www-and-celery celery
        sudo usermod -a -G www-and-celery www-data

        # give the group read-write access to logs
        sudo chgrp -R www-and-celery /var/log/django
        sudo chmod -R 775 /var/log/django

        # give the group read-write access to database
        sudo chgrp -R www-and-celery /var/databases
        sudo chmod -R 775 /var/databases


Create Celery configuration files
"""""""""""""""""""""""""""""""""

Next, you'll need to create three Celery configuration files for PolicyKit:

``/etc/conf.d/celery-policykit``
""""""""""""""""""""""""""""""""

.. code-block:: bash

        CELERYD_NODES="w1"

        # Absolute or relative path to the 'celery' command:
        CELERY_BIN="$POLICYKIT_ENV/bin/celery"

        # App instance to use
        CELERY_APP="policykit"

        # How to call manage.py
        CELERYD_MULTI="multi"

        # Extra command-line arguments to the worker
        CELERYD_OPTS="--time-limit=300 --concurrency=8"

        # - %n will be replaced with the first part of the nodename.
        # - %I will be replaced with the current child process index
        #   and is important when using the prefork pool to avoid race conditions.
        CELERYD_PID_FILE="/var/run/celery/%n.pid"
        CELERYD_LOG_FILE="/var/log/celery/%n%I.log"
        CELERYD_LOG_LEVEL="INFO"

        # you may wish to add these options for Celery Beat
        CELERYBEAT_PID_FILE="/var/run/celery/policykit_beat.pid"
        CELERYBEAT_LOG_FILE="/var/log/celery/policykit_beat.log"


``/etc/systemd/system/celery-policykit.service``
""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: bash

        [Unit]
        Description=Celery Service
        After=network.target

        [Service]
        Type=forking
        User=celery
        Group=celery
        EnvironmentFile=/etc/conf.d/celery-policykit
        WorkingDirectory=$POLICYKIT_REPO/policykit
        ExecStart=/bin/sh -c '${CELERY_BIN} multi start ${CELERYD_NODES} \
        -A ${CELERY_APP} --pidfile=${CELERYD_PID_FILE} \
        --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}'
        ExecStop=/bin/sh -c '${CELERY_BIN} multi stopwait ${CELERYD_NODES} \
        --pidfile=${CELERYD_PID_FILE}'
        ExecReload=/bin/sh -c '${CELERY_BIN} multi restart ${CELERYD_NODES} \
        -A ${CELERY_APP} --pidfile=${CELERYD_PID_FILE} \
        --logfile=${CELERYD_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} ${CELERYD_OPTS}'

        [Install]
        WantedBy=multi-user.target


``/etc/systemd/system/celerybeat-policykit.service``
""""""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: bash

        [Unit]
        Description=Celery Beat Service
        After=network.target

        [Service]
        Type=simple
        User=celery
        Group=celery
        EnvironmentFile=/etc/conf.d/celery-policykit
        WorkingDirectory=$POLICYKIT_REPO/policykit
        ExecStart=/bin/sh -c '${CELERY_BIN} -A ${CELERY_APP}  \
        beat --pidfile=${CELERYBEAT_PID_FILE} \
        --logfile=${CELERYBEAT_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} \
        --schedule=/var/run/celery/celerybeat-policykit-schedule'

        [Install]
        WantedBy=multi-user.target


| After creating the files (and after any time you change them) run the following command:

::

 sudo systemctl daemon-reload

| Finally, run the following commands to start the celery daemon:

::

 sudo service rabbitmq-server start
 sudo systemctl start celery-policykit celerybeat-policykit

| Verify that there are no errors with celery and celerybeat by running these commands:

::

 sudo systemctl status celery-policykit
 sudo systemctl status celerybeat-policykit

Troubleshooting
"""""""""""""""

| If celery or celerybeat fail to start up as a service, try running celery directly to see if there are errors in your code:

::

 celery -A policykit worker -l info --uid celery
 celery -A policykit beat -l info --uid celery --schedule=/var/run/celery/celerybeat-policykit-schedule


If celerybeat experiences errors starting up, check the logs at ``/var/log/celery/policykit_beat.log``.

Set up Integrations
^^^^^^^^^^^^^^^^^^^

Before your instance of PolicyKit can be installed onto external platforms,
you'll need to go through setup steps for each :doc:`integration <integrations>`
that you want to support:


Metagov
"""""""

1. Deploy an instance of Metagov on the same machine as PolicyKit. See `Installing Metagov <https://docs.metagov.org/en/latest/installation.html>`_ for instructions.
2. In the ``.env`` file in Metagov, set the URL for receiving events: ``DRIVER_EVENT_RECEIVER_URL=[POLICYKIT_URL]/metagov/internal/action``
3. To enable Metagov in PolicyKit, set the ``METAGOV_URL`` in your ``private.py`` file to point to your Metagov instance.
4. Ensure that ``/metagov/internal`` is restricted to local traffic. Follow the Apache2 example above.

Slack
"""""
The Slack integration occurs through Metagov. Follow the setup instructions for the Metagov Slack Plugin to create a new Slack App to use with PolicyKit.

Discord
"""""""

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

Discourse
"""""""""

There is no admin setup required for Discourse.
Each Discourse community that installs PolicyKit needs to register the PolicyKit auth redirect separately.

Reddit
""""""

1. Create a new app at https://www.reddit.com/prefs/apps
2. Set the ``REDDIT_CLIENT_SECRET`` in ``private.py``.
3. Reload apache2: ``systemctl reload apache2``
