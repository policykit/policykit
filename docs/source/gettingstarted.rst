.. _start:

Installation and Getting Started
====================================

| On this page, we will take you through the process of setting up PolicyKit, both for development and for production.

Getting Started
---------------

| PolicyKit requires Python 3. Before you install, we recommend that you activate a Python 3+ virtual environment.

| To begin, you need to download PolicyKit from our `GitHub repository <https://github.com/amyxzhang/policykit>`_. Once you have finished downloading PolicyKit, change to that directory by doing:

::

 cd policykit

| From here, run the following command to install PolicyKit's dependencies:

::

 pip install -r requirements.txt

| Next, run the following command to create a file to store your API keys:

::

 cp private_template.py private.py

| PolicyKit requires a directory to send logs to. By default, it logs to the path ``/var/log/django``. You either need to create a folder at this path or edit the ``LOGGING`` field in ``settings.py`` to point to the right location.

| To verify that you have set the PolicyKit server up correctly, run the following command:

::

 python manage.py runserver

| To use PolicyKit, you must set up your own database. You can use the default ``sqlite`` or ``mysql`` or another database of your choice. Edit the ``DATABASES`` field in ``settings.py`` to point to the right database.

| Once you have finished setting up your database, run the following commands to create and apply new migrations:

::

 python manage.py makemigrations
 python manage.py migrate

| Finally, you need to set up PolicyKit's governance starter kits. Run the following command to enter the shell:

::

 python manage.py shell

From the shell prompt, run the following command to create the starterkits:

::

 exec(open('scripts/starterkits.py').read())

Open PolicyKit in the browser at http://localhost:8000/main

Troubleshooting
^^^^^^^^^^^^^^^

| It's possible that you may receive the error ``InvalidBasesError: Cannot resolve bases for [<ModelState: 'users.GroupProxy'>]`` where ``ModelState`` may refer to ``policyengine``, ``policykit``, ``slack``, ``reddit``, ``discord`` or ``discourse``. If so, inside each referenced directory, make sure that there exists a subdirectory named ``migrations`` containing an empty file named ``__init__.py``.

| It's possible that when you try to make migrations, you may receive an error of the form ``ImportError: cannot import name 'FieldDoesNotExist'``. If you receive this error, then you need to go to ``/site-packages/polymorphic/query.py`` and change the line ``django.db.models import FieldDoesNotExist`` to ``from django.core.exceptions import FieldDoesNotExist``.

Running PolicyKit in Production
-------------------------------

| Thus far, we have been run in Ubuntu 18.04 and Ubuntu 20.04, and the below instructions should work for both.

| Add PolicyKit to the server by uploading the codebase or using ``git clone``. Create a virtualenv and install all requirements into the virtualenv as above. For instructions, see `this guide <https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-programming-environment-on-an-ubuntu-20-04-server>`_.

| Once you have finished following the earlier guide to setting up PolicyKit, you need to make the following additional changes:

- Update the ``SERVER_URL`` field in ``private.py``, and fill in any necessary API keys/secrets.

- Update the ``ALLOWED_HOSTS`` field in ``settings.py`` to point to your host.

- Update that the database path in ``settings.py`` under ``DATABASES``. It is not recommended to keep the database inside the project directory, because the apache2 user (www-data) needs write access to the database *and* it's parent folder. Recommended: put the database in ``/var/databases/policykit/db.sqlite3``.

- Update the ``LOGGING_ROOT_DIR``in ``settings.py`` to point to your log directory (for example ``/var/log/django``).

- Generate a new Django secret key and put it in ``settings.py``. Generate a key with this command:

        .. code-block::

                python manage.py shell -c 'from django.core.management import utils; print(utils.get_random_secret_key())'


| Next, run the following command to collect static files into a ``static/`` folder:

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

                        WSGIDaemonProcess policykit python-home=$POLICYKIT_ENV python-path=$POLICYKIT_REPO/policykit
                        WSGIProcessGroup policykit
                        WSGIScriptAlias / $POLICYKIT_REPO/policykit/policykit/wsgi.py
                        # .. REST ELIDED
                </VirtualHost>
        </IfModule>

4. Test your config with ``apache2ctl configtest``

5. Get an SSL certificate and set it up to auto-renew using LetsEncrypt. Follow step 4 here: `How To Secure Apache with Let's Encrypt on Ubuntu 20.04 <https://www.digitalocean.com/community/tutorials/how-to-secure-apache-with-let-s-encrypt-on-ubuntu-20-04>`_. Once that's done, add the newly created SSL files to your apache2 conf:

    .. code-block:: aconf

        SSLCertificateFile /etc/letsencrypt/live/$SERVER_NAME/fullchain.pem
        SSLCertificateKeyFile /etc/letsencrypt/live/$SERVER_NAME/privkey.pem

6. Activate the site:

        .. code-block:: shell

             a2ensite /etc/apache2/sites-available/$SERVER_NAME.conf
             # you should see a symlink to your site config here:
             ls /etc/apache2/sites-enabled

7. Load your site in the browser.

  Check for errors at ``/var/log/apache2/error.log`` and ``/var/log/django/debug.log`` (or whatever logging path you have defined in ``settings.py``). The ``www-data`` user should own the Django log directory and have write-access to the log file.

8. Any time you update the code, you'll need to run ``systemctl reload apache2`` to reload the server.

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

Install RabbitMQ:

.. code-block:: shell

    sudo apt-get install rabbitmq-server

Follow these instruction to `create a RabbitMQ username, password, and virtual host <https://docs.celeryproject.org/en/stable/getting-started/brokers/rabbitmq.html#setting-up-rabbitmq>`_.

In ``policykit/settings.py``, set the ``CELERY_BROKER_URL`` as follows, substituting values for your RabbitMQ username, password, and virtual host:

.. code-block:: python

    CELERY_BROKER_URL = "amqp://USERNAME:PASSWORD@localhost:5672/VIRTUALHOST"

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

| Finally, run the following commands to start the server:

::

 sudo service apache2 start
 sudo service rabbitmq-server start
 sudo systemctl start celery-policykit celerybeat-policykit

| Verify that there are no errors with celery and celerybeat by running these commands:

::

 sudo systemctl status celery-policykit
 sudo systemctl status celerybeat-policykit

| Once things are up and running, you should be able to access the PolicyKit editor in the browser at ``https://<your domain>/main``.

Troubleshooting
"""""""""""""""

| If celery or celerybeat fail to start up as a service, try running celery directly to see if there are errors in your code:

::

 celery -A policykit worker -l info --uid celery
 celery -A policykit beat -l info --uid celery --schedule=/var/run/celery/celerybeat-policykit-schedule


If celerybeat experiences errors starting up, check the logs at ``/var/log/celery/beat.log``.
