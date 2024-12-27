
##
# Set the `FORCE_SLACK_LOGIN=<readable name>` env variable to force login as a specific user, without having to authenticate.
# Helpful for development.
##


from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.utils.deprecation import MiddlewareMixin

from integrations.slack.models import SlackUser

User = get_user_model()

class ForceLoginMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if settings.FORCE_SLACK_LOGIN:
            user = SlackUser.objects.get(readable_name=settings.FORCE_SLACK_LOGIN)
            user.backend = 'integrations.slack.auth_backends.SlackBackend'
            login(request, user)

