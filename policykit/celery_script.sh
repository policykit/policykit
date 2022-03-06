#! /bin/bash

useradd celery -d /home/celery -b /bin/bash
mkdir /var/log/celery
chown -R celery:celery /metagov/metagov
chown -R celery:celery /var/log/celery
chmod -R 755 /var/log/celery

mkdir /var/run/celery
chown -R celery:celery /var/run/celery
chmod -R 755 /var/run/celery

groupadd www-and-celery
usermod -a -G www-and-celery celery
usermod -a -G www-and-celery www-data

# give the group read-write access to logs
mkdir -p /var/log/django
chgrp -R www-and-celery /var/log/django
chmod -R 775 /var/log/django
