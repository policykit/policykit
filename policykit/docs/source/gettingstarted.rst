.. _start:

Installation and Getting Started
====================================

On this page, we will take you through the process of setting up PolicyKit, both for development and for production.

Getting Started
~~~~~~~~~~~~~~~~~

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

Troubleshooting
---------------------------

| It's possible that you may receive the error ``InvalidBasesError: Cannot resolve bases for [<ModelState: 'users.GroupProxy'>]`` where ``ModelState`` may refer to ``policyengine``, ``policykit``, ``slack``, ``reddit``, ``discord`` or ``discourse``. If so, inside each referenced directory, make sure that there exists a subdirectory named ``migrations`` containing an empty file named ``__init__.py``.

| It's possible that when you try to make migrations, you may receive an error of the form ``ImportError: cannot import name 'FieldDoesNotExist'``. If you receive this error, then you need to go to ``/site-packages/polymorphic/query.py`` and change the line ``django.db.models import FieldDoesNotExist`` to ``from django.core.exceptions import FieldDoesNotExist``.

Running PolicyKit in Production
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

| Initialize a webserver. Thus far, we have been run in Ubuntu 18.04 and Ubuntu 20.04, and the below instructions should work for both.

| Add PolicyKit to the server by uploading the codebase or using ``git clone``. Create a virtualenv and install all requirements into the virtualenv as above. For instructions, see `this guide <https://www.digitalocean.com/community/tutorials/how-to-install-python-3-and-set-up-a-programming-environment-on-an-ubuntu-20-04-server>`_.

| Once you have finished following the earlier guide to setting up PolicyKit you need to make the following additional changes:

- Update the ``ALLOWED_HOSTS`` field in ``settings.py`` to point to your hosts.

- Update the ``SERVER_URL`` field in ``private.py``, and fill in any necessary API keys/secrets.

- Verify that the database path in ``settings.py`` is correct. It is not recommended to keep the database inside the project directory, because you need to grant the apache2 user (``www-data``) access to the database its parent folder. Recommended: put the database somewhere like ``/var/databases/policykit/db.sqlite3``.

| Next, run the following command to collect static files into a ``static/`` folder:

::

 python manage.py collectstatic

| Run the following command to install Apache2 and the ``mod-wsgi`` package:

::

 sudo apt-get install apache2 libapache2-mod-wsgi-py3

| Configure Apache2 by editing ``/etc/apache2/sites-available/000-default.conf``. Note: By default, this config file assumes the code is at ``/policykit`` and the virtualenv is at ``/policykit_vm``.

| File: ``000-default.conf``

::

 <VirtualHost *:80>
        Alias /static /policykit/policykit/static
        <Directory /policykit/policykit/static>
                Require all granted
        </Directory>

        <Directory /policykit/policykit/policykit>
                <Files wsgi.py>
                        Require all granted
                </Files>
        </Directory>

        WSGIDaemonProcess policykit python-home=/policykit_vm python-path=/policykit/policykit
        WSGIProcessGroup policykit
        WSGIScriptAlias / /policykit/policykit/policykit/wsgi.py

 ...more below

| You may separately wish to configure PolicyKit to work under HTTPS (will be neccesary to interface with the Slack API for instance). If so, you'll need to get an SSL certificate (we use LetsEncrypt) and add the following file under ``/etc/apache2/sites-available/default-ssl.conf``. You may want to redirect HTTP calls to HTTPS - if so, you'll need to update the :80 config above. `Instructions to set up LetsEncrypt on ubuntu 20.04 <https://www.digitalocean.com/community/tutorials/how-to-secure-apache-with-let-s-encrypt-on-ubuntu-20-04>`_.

::

 #<IfModule mod_ssl.c>
        <VirtualHost *:443>
                Alias /static /policykit/policykit/static
                <Directory /policykit/policykit/static>
                        Require all granted
                </Directory>

                <Directory /policykit/policykit/policykit>
                        <Files wsgi.py>
                                Require all granted
                        </Files>
                </Directory>

                WSGIDaemonProcess policykitssl python-home=/policykit_vm python-path=/policykit/policykit
                WSGIProcessGroup policykitssl
                WSGIScriptAlias / /policykit/policykit/policykit/wsgi.py

                SSLEngine on
                SSLCertificateFile      /etc/letsencrypt/live/policykit.org/fullchain.pem
                SSLCertificateKeyFile /etc/letsencrypt/live/policykit.org/privkey.pem

 ...more below

| Run the following commands to install ``RabbitMQ`` and ``celery``:

::

 sudo apt-get install rabbitmq-server
 pip install celery

| Next, we need to create these configuration files for running ``celery`` and ``celery-beat`` as a process:

| File: ``/etc/systemd/system/celery.service``

::

 [Unit]
 Description=Celery Service
 After=network.target

 [Service]
 Type=forking
 User=ubuntu
 Group=ubuntu
 EnvironmentFile=/etc/conf.d/celery
 WorkingDirectory=/policykit/policykit
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

| File: ``/etc/systemd/system/celerybeat.service``

::

 [Unit]
 Description=Celery Beat Service
 After=network.target

 [Service]
 Type=simple
 User=ubuntu
 Group=ubuntu
 EnvironmentFile=/etc/conf.d/celery
 WorkingDirectory=/policykit/policykit
 ExecStart=/bin/sh -c '${CELERY_BIN} beat  \
   -A ${CELERY_APP} --pidfile=${CELERYBEAT_PID_FILE} \
   --logfile=${CELERYBEAT_LOG_FILE} --loglevel=${CELERYD_LOG_LEVEL}'

 [Install]
 WantedBy=multi-user.target

| You can see both point to an environment file. Add the following file. You can change the arguments to suit your needs. Make sure to update the path to Celery bin according to your virtual environment.

| File: ``/etc/conf.d/celery``

::

 # Name of nodes to start
 # we have one node:
 CELERYD_NODES="w1"

 # Absolute or relative path to the 'celery' command:
 CELERY_BIN="/policykit_vm/bin/celery"

 # App instance to use
 # comment out this line if you don't use an app
 CELERY_APP="policykit"
 # or fully qualified:
 #CELERY_APP="proj.tasks:app"

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

| See `Celery 4.4.0 docs for daemonization using systemd <https://docs.celeryproject.org/en/4.4.0/userguide/daemonizing.html#usage-systemd>`_ for more information.

| After creating the files (and after any time you change them) run the following command:

::

 sudo systemctl daemon-reload

| Finally, run the following commands to start the server:

::

 sudo service apache2 start
 sudo service rabbitmq-server start
 sudo systemctl start celery.service
 sudo systemctl start celerybeat.service

| Verify that there are no errors with celery and celerybeat by running these commands:

::

 sudo systemctl status celery
 sudo systemctl status celerybeat

Troubleshooting
----------------

| If celery failed to start up as a service, try running celery directly to see if there are errors in your code:

::

 celery worker --uid <User that runs celery> -A policykit

If celerybeat experiences errors starting up, check the logs at ``/var/log/celery/beat.log``.
