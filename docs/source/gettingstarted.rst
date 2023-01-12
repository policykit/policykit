.. _start:

Installation and Getting Started
====================================

On this page, we will take you through the process of setting up PolicyKit, both for local development and on an Ubuntu server.

Local Development
-----------------

PolicyKit requires Python 3. Before you install, we recommend that you activate a Python 3+ virtual environment.

To begin, clone the `PolicyKit GitHub repository <https://github.com/amyxzhang/policykit>`_ (or your fork) and navigate to the python project root:

::

 git clone https://github.com/amyxzhang/policykit.git
 cd policykit/policykit

From here, run the following commands to install PolicyKit's dependencies:

::

 pip install --upgrade pip
 pip install -r requirements.txt

Next, run the following command to create a file to store your settings and secrets:

::

 cd policykit
 cp .env.example .env

To run PolicyKit in production, you'll need to change some values in the ``.env`` file such as the ``DJANGO_SECRET_KEY`` and ``SERVER_URL``. For local development, all you need to do is set ``DEBUG=true``.

Navigate up a directory 

::

 cd ..

To verify that you have set the PolicyKit server up correctly, run the following command:

::

 python manage.py runserver

By default, PolicyKit will create a sqlite3 database in the root directory. If you want to use another database, you can edit the ``DATABASES`` field in ``settings.py``.

Exit the server with control-c

Run the following command to create and set up the database:

::

 python manage.py migrate

Open PolicyKit in the browser at http://localhost:8000/main. At this point, you won't be able to log in because PolicyKit currently only supports sign-in via external auth providers (Slack, Discord, Reddit, and Discourse).
There is an open issue to support logging in without any third-party platform: `#514 <https://github.com/amyxzhang/policykit/issues/514>`_.

To log in to PolicyKit, you'll need to install it on a dev server and set up at least 1 of the auth-enabled integrations.


Running PolicyKit on a Server
-----------------------------

Thus far, we have run Policykit in Ubuntu 18.04 and Ubuntu 20.04. The instructions below should work for both.

1. Add PolicyKit to the server by uploading the codebase or using ``git clone`` in ``/var/www/policykit`` or similar.

           .. code-block::

                    git clone <repo>
                    cd <repo>

2. Follow `this guide <https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-programming-environment-on-an-ubuntu-20-04-server>`_ to install Python3 and to create a virtual environment for PolicyKit.
   - Creating a virtual invironment:
         
           .. code-block::

                    sudo apt install python3-pip python3-venv
                    python3 -m venv policykit_venv
                    source policykit_venv/bin/activate

Your terminal prompt should change to look something like this ``(policykit_venv)user@host:~/myproject$``.

3. Install the requirements to the virtual environment with ``pip install -r requirements.txt``.
   - Navigate to /policykit/policykit:
         
           .. code-block::

                    cd policykit
                    pip install --upgrade pip
                    pip install -r requirements.txt

4. Next, run the following command to create a file to store your settings and secrets:
           
           .. code-block::
                   
                   cd policykit
                   cp .env.example .env
 
5. Make the following additional changes to ``.env``:

   - Set the ``DJANGO_SECRET_KEY`` field. Generate a key in the previous directory with this command:

           .. code-block::

                   python manage.py shell -c 'from django.core.management import utils; print(utils.get_random_secret_key())'

   - Set the ``SERVER_URL`` field.
   - Set the ``ALLOWED_HOSTS`` field to point to your host.
   - Make sure ``DEBUG`` is empty or set to false.
   - Be sure to uncomment these fields by removing the ``#`` at the start of a line.
   - You can leave the platform integration API keys/secrets empty for now. Follow the instructions under "Set up Integrations" to set up each integration.

6. If you want to use a database other than dbsqlite3, or if you want to change the database path, update the ``DATABASES`` object in ``settings.py``.

7. To verify that you have set the PolicyKit server up correctly, run the following command:

::

python manage.py runserver

By default, this command will make PolicyKit create a sqlite3 database in the base directory where manage.py is stored. If you want to use another database, or stor the database in another location, you can edit the ``DATABASES`` field in ``settings.py``.

If you want to see the server in development mode, refer to the previous section.

Exit the server with control-c

8. Run the following command to create and set up the database:

::

python manage.py migrate

9. Next, run the following command to collect static files into a ``static/`` folder:

::

python manage.py collectstatic


Deploy with Apache web server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now that you have PolicyKit installed on your server, you can deploy it on Apache web server.
Make sure you have a domain dedicated to Policykit that is pointing to your server's IP address.

.. note::

        In the remaining examples, make sure to substitute the following values used in the Apache config files with an absolute path:

        ``$POLICYKIT_REPO`` is the path to your policykit repository root. (``/policykit``)

        ``$POLICYKIT_ENV`` is the path to your policykit virtual environment. (``/policykit_venv``)

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
                        DocumentRoot $POLICYKIT_REPO
                        
                        # Grant access to the static site 
                        <Directory $POLICYKIT_REPO/policykit/static>
                                Require all granted
                        </Directory>

                        # Grant access to wsgi.py file. This is the Django server.
                        <Directory $POLICYKIT_REPO/policykit/policykit>
                                <Files wsgi.py>
                                        Require all granted
                                </Files>
                        </Directory>
                        
                        # Setup the WSGI Daemon
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

                # disable the default ssl config
                sudo a2dissite default-ssl.conf

6. Get an SSL certificate and set it up to auto-renew using LetsEncrypt:

    .. code-block:: shell

        sudo apt install certbot python3-certbot-apache
        sudo certbot --apache

7. Add the certificates to your ``$SERVER_NAME.conf`` file (certbot may auto-inject this code at the bottom of your .conf):

    .. code-block:: aconf

        SSLCertificateFile /etc/letsencrypt/live/$SERVER_NAME/fullchain.pem
        SSLCertificateKeyFile /etc/letsencrypt/live/$SERVER_NAME/privkey.pem

8. Reload the config:

     .. code-block:: shell

          systemctl reload apache2


9. Change the permission so the group owner of the database and the logging files can read and write. If using sqlite, the database is called db.sqlite3, and the logging file is called debug.log (update paths as needed based on personal setup, you may need to make the following directories if you want to follow this file system architecture):

        .. code-block:: shell

                sudo chmod 664 /var/log/django/policykit/policykit/debug.log
                sudo chmod 664 /var/databases/policykit/policykik/db.sqlite3

10. Give the Apache2 user access to the database directory (if using sqlite) and the logging directory (update paths as needed based on personal setup):

        .. code-block:: shell

                sudo chown -R www-data:www-data /var/django/policykit/policykit
                sudo chown -R www-data:www-data /var/databases/policykit/policykit
                

10. Load your site in the browser and navigate to ``/login``. You should see a site titled "Django adminstration" with options to connect to Slack, Reddit, Discourse, and Discord. Before you can install PolicyKit into any of these platforms, you'll need to set the necessary client IDs and client in ``private.py``. Follow the setup instructions for each integration in :doc:`Integrations <../integrations>`.

  Check for errors at ``/var/log/apache2/error.log`` and ``/var/www/policykit/policykit/debug.log`` (or whatever logging path you set in  ``.env``). 

11. Any time you update the code, you'll need to run ``systemctl reload apache2`` to reload the server.

Set up Celery
^^^^^^^^^^^^^

PolicyKit uses `Celery <https://docs.celeryproject.org/en/stable/index.html>`_ to run scheduled tasks.
Follow these instructions to run a celery daemon on your Ubuntu machine using ``systemd``.
For more information about configuration options, see the `Celery Daemonization <https://docs.celeryproject.org/en/stable/userguide/daemonizing.html>`_.


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

        # give the group read-write access to database (if using sqlite)
        sudo chgrp -R www-and-celery /var/databases
        sudo chmod -R 775 /var/databases


Create Celery configuration files
"""""""""""""""""""""""""""""""""

Next, you'll need to create three Celery configuration files for PolicyKit (remember to change variables such as ``$POLICYKIT_ENV`` to their relative or absolute path in your OS):

``/etc/conf.d/celery``
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
        CELERYBEAT_PID_FILE="/var/run/celery/beat.pid"
        CELERYBEAT_LOG_FILE="/var/log/celery/beat.log"


``/etc/systemd/system/celery.service``
""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: bash

        [Unit]
        Description=Celery Service
        After=network.target

        [Service]
        Type=forking
        User=celery
        Group=celery
        EnvironmentFile=/etc/conf.d/celery
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


``/etc/systemd/system/celerybeat.service``
""""""""""""""""""""""""""""""""""""""""""""""""""""

.. code-block:: bash

        [Unit]
        Description=Celery Beat Service
        After=network.target

        [Service]
        Type=simple
        User=celery
        Group=celery
        EnvironmentFile=/etc/conf.d/celery
        WorkingDirectory=$POLICYKIT_REPO/policykit
        ExecStart=/bin/sh -c '${CELERY_BIN} -A ${CELERY_APP}  \
        beat --pidfile=${CELERYBEAT_PID_FILE} \
        --logfile=${CELERYBEAT_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL} \
        --schedule=/var/run/celery/celerybeat-schedule'

        [Install]
        WantedBy=multi-user.target


| After creating the files (and after any time you change them) run the following command:

::

 sudo systemctl daemon-reload

| Next, install and setup a message broker RabbitMQ 

::

 sudo apt-get install erlang rabbitmq-server

| Then enable and start the RabbitMQ service:

:: 

 sudo systemctl enable rabbitmq-server
 sudo service rabbitmq-server start

| Check the status to make sure everything is running smoothly:

::

 systemctl status rabbitmq-server

| Finally, run the following commands to start the celery daemon:

::
 
 sudo systemctl start celery celerybeat

| Verify that there are no errors with celery and celerybeat by running these commands:

::

 sudo systemctl status celery
 sudo systemctl status celerybeat

Troubleshooting
"""""""""""""""

| If celery or celerybeat fail to start up as a service, try running celery directly to see if there are errors in your code:

::

 celery -A policykit worker -l info --uid celery
 celery -A policykit beat -l info --uid celery --schedule=/var/run/celery/celerybeat-schedule


If celerybeat experiences errors starting up, check the logs at ``/var/log/celery/beat.log``.


Interactive Django Shell
^^^^^^^^^^^^^^^^^^^^^^^^

The interactive Django shell can be useful when developing and debugging PolicyKit.
Access the Django shell with ``python manage.py shell_plus``.
Some useful shell commands for development:

.. code-block:: bash

        # List all communities
        Community.objects.all()

        # List CommunityPlatforms for a specific community
        community = Community.objects.first()
        CommunityPlatform.objects.filter(community=community)

        # Get all pending proposals
        Proposal.objects.filter(status="proposed")

        # Manually run the policy checking task that is executed on a schedule by Celery
        from policyengine.tasks import evaluate_pending_proposals
        evaluate_pending_proposals()

        ###### Advanced Commands for debugging Metagov ######

        # Access the Metagov Community model
        from metagov.core.models import Community as MetagovCommunity
        MetagovCommunity.objects.all()
        MetagovCommunity.objects.get(slug=community.metagov_slug)

        # Access the Metagov Plugin models (1:1 with CommunityPlatform)
        Plugin.objects.all()
        Slack.objects.all()
        Plugin.objects.filter(community__slug=community.metagov_slug)

        # Get pending Metagov GovernanceProcesses
        GovernanceProcess.objects.filter(status='pending')
        GovernanceProcess.objects.filter(plugin__community=metagov_community)
        SlackEmojiVote.objects.filter(status='pending', plugin__community__slug="my-slug")


Set up Integrations
^^^^^^^^^^^^^^^^^^^

Before your instance of PolicyKit can be installed onto external platforms,
you'll need to go through setup steps for each :doc:`integration <integrations>`
that you want to support:


Slack
"""""
The Slack integration occurs through Metagov. Follow the setup instructions for the Metagov Slack Plugin to create a new Slack App to use with PolicyKit.


Discord
"""""""
The Discord integration occurs through Metagov. Follow the setup instructions for the Metagov Discord Plugin to create a new Discord App to use with PolicyKit.

Discourse
"""""""""

There is no admin setup required for Discourse.
Each Discourse community that installs PolicyKit needs to register the PolicyKit auth redirect separately.

Reddit
""""""

1. Create a new app at https://www.reddit.com/prefs/apps
2. Set the ``REDDIT_CLIENT_SECRET`` in ``private.py``.
3. Reload apache2: ``systemctl reload apache2``

Developing the Metagov Gateway
------------------------------

If you're making changes to the `Metagov Gateway <https://docs.metagov.org/>`_ and want to test those changes in PolicyKit, you have two options:

   1. Push your changes to a branch or fork, and update ``requirements.txt`` in PolicyKit to point to it:

     .. code-block:: bash

        -e git+https://github.com/metagov/gateway.git@<your-dev-branch>#egg=metagov&subdirectory=metagov

   2. Use pip "editable" installs to point to your local Metagov Gateway codebase:

     .. code-block:: bash

        pip install -e /path/to/gateway/repo/metagov
