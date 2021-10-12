import urllib.parse

from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views
from django.urls import path
from policyengine import views as policyviews
from django.conf import settings
# from schema_graph.views import Schema

urlpatterns = [
    path('login/', views.LoginView.as_view(
        template_name='policyadmin/login.html',
        extra_context={
            'server_url': urllib.parse.quote(settings.SERVER_URL, safe=''),
            'metagov_server_url': settings.METAGOV_URL,
            'reddit_client_id': settings.REDDIT_CLIENT_ID,
            'discord_client_id': settings.DISCORD_CLIENT_ID,
        }
    )),
    path('authorize-platform', policyviews.authorize_platform),
    path('logout/', policyviews.logout, name="logout"),
    path('main/', policyviews.v2),
    path('main/editor/', policyviews.editor),
    path('main/selectrole/', policyviews.selectrole),
    path('main/roleusers/', policyviews.roleusers),
    path('main/roleeditor/', policyviews.roleeditor),
    path('main/selectpolicy/', policyviews.selectpolicy),
    path('main/documenteditor/', policyviews.documenteditor),
    path('main/selectdocument/', policyviews.selectdocument),
    path('main/actions/', policyviews.actions),
    path('main/actions/<str:app_name>/<str:codename>', policyviews.propose_action),
    path('main/policyengine/', include('policyengine.urls')),
    path('main/settings/', policyviews.settings_page, name="settings"),
    path('main/settings/addintegration', policyviews.add_integration, name="add_integration"),
    path('main/logs/', include('django_db_logger.urls', namespace='django_db_logger')),
    path('admin/', admin.site.urls),
    path('slack/', include('integrations.slack.urls')),
    path('reddit/', include('integrations.reddit.urls')),
    path('discord/', include('integrations.discord.urls')),
    path('discourse/', include('integrations.discourse.urls')),
    path('github/', include('integrations.github.urls')),
    path('opencollective/', include('integrations.opencollective.urls')),
    url(r'^$', policyviews.homepage),
    url('^activity/', include('actstream.urls')),
    # path("schema/", Schema.as_view()),
]

if settings.METAGOV_ENABLED:
    urlpatterns += [path('metagov/', include('integrations.metagov.urls'))]
