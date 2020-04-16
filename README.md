# PolicyKit

## Getting Started
`pip install -r requirements.txt`

Put `CLIENT_SECRET = ""` in settings.py

`python3 manage.py runserver`

Run Migrations

Had issue with LOGGING filename...
Need to change where debug log goes or create folder /var/log/django

For django-jet to run with Django 3.0:

Find the `jet/dashboard/models.py` and `"jet/models.py"` files in your django-jet instllation and replace the line `from django.utils.encoding import python_2_unicode_compatible` with `from six import python_2_unicode_compatible`

Note: I ran into some issues with permissions, remember to install with sudo if executing requires sudo.