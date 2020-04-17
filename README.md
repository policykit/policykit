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
Check you can run the server with no problems:
`python manage.py runserver`

6)
Now set up a database. You can use the default sqlite or mysql or another database of your choice. Make sure settings.py is pointing to the right database.

Finally, run `python manage.py makemigrations` to migrate tables to the database.

## Potential Issues

1)
It's possible that you may receive an error saying that installing from requirements.txt fails on the line `-pkg-resources==0.0.0`. If so, delete this line from requirements.txt and re-install.

2)
It's possible that you may receive the error `InvalidBasesError: Cannot resolve bases for [<ModelState: 'users.GroupProxy'>]` where `ModelState` may refer to policyengine, policykit, redditintegration or slackintegration. If so, inside each subdirectory: policyengine, policykit, redditintegration and slackintegration, create a directory called `migrations` and add an empty file inside each directory named `__init__.py`.
