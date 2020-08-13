# PolicyKit

## Getting Started

1)
PolicyKit requires python 3.

I recommend that you use virtualenv.
Once you have that created, activate the virtualenv and run:

`pip install -r requirements.txt`

2)
One of our libraries, django-jet, does not work with Django 3.0 yet.
To fix this, find the `jet/dashboard/models.py` and `jet/models.py` files in your django-jet installation.
If you used virtualenv, this should be in path_to_your_ve/your_ve_name/lib/python3.7/site-packages/jet/

In both files, replace the line `from django.utils.encoding import python_2_unicode_compatible` with `from six import python_2_unicode_compatible`

3)
Put
`SLACK_CLIENT_SECRET = ''`
`REDDIT_CLIENT_SECRET = ''`
in a file called private.py in the same file as your manage.py file. These store API secret keys that you will need to fill out if you wish to query the Slack or Reddit API.

4)
PolicyKit is currently logging to the path: /var/log/django
You either need to create this folder or go into settings.py to change where it logs.

5)
Rename private_template.py to private.py. Fill in the variables with your API ids and secrets for the platforms you wish to integrate with.

6)
Check you can run the server with no problems:
`python manage.py runserver`

7)
Now set up a database. You can use the default sqlite or mysql or another database of your choice. Make sure settings.py is pointing to the right database.

Finally, run `python manage.py makemigrations` to migrate tables to the database.

8)
Run the script 'policyengine/scripts/starterkits.py'. This sets up the starter systems of governance that you can choose to integrate into your community. In order to do so, first enter the shell with `python manage.py shell`, then run `exec(open('policyengine/scripts/starterkits.py').read())`. 

## Potential Issues

1)
It's possible that you may receive the error `InvalidBasesError: Cannot resolve bases for [<ModelState: 'users.GroupProxy'>]` where `ModelState` may refer to policyengine, policykit, redditintegration or slackintegration. If so, inside each subdirectory: policyengine, policykit, redditintegration and slackintegration, create a directory called `migrations` and add an empty file inside each directory named `__init__.py`.


## Running PolicyKit in Production

Initialize a webserver. Thus far, we have been running in Ubuntu 18.04, and the below instructions work for that OS. 

Add PolicyKit to the server by uploading the codebase or using `git clone`. Create a virtualenv and install all requirements into the virtualenv as above.

Remember to run `python manage.py collectstatic` to collect static files into a static/ folder.


Install Apache2.

Configure Apache2 by editing /etc/apache2/sites-available/000-default.conf. This config file assumes the code is at /policykit and the virtualenv is at /policykit_vm.

File: 000-default.conf
```
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
```

You may separately wish to configure PolicyKit to work under HTTPS (will be neccesary to interface with the Slack API for instance). If so, you'll need to get an SSL certificate (we use LetsEncrypt) and add the following file under /etc/apache2/sites-available/default-ssl.conf. You may want to redirect HTTP calls to HTTPS - if so, you'll need to update the :80 config above.

```
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
```

Start apache2:
`sudo service apache2 start`




Install RabbitMQ, Celery, and celery-beat.

Start RabbitMQ:
`sudo service rabbitmq-server start`

Inside /etc/systemd/system add configuration files for running celery and celery-beat as a process:

File: celery.service
```
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
```

File: celerybeat.service
```
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
```

You can see both point to an environment file. In /etc/conf.d add the following file. You can change the arguments to suit your needs.

Filename: celery
```
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
```

Start celery:
`sudo systemctl start celery.service`

Start celerybeat:
`sudo systemctl start celerybeat.service`


