from django.contrib import admin
from django.contrib.auth import views
from django.urls import path
from django.conf.urls import include, url
from django.views.generic import TemplateView
from django.shortcuts import redirect
import urllib.parse
from policykit.settings import SERVER_URL, SLACK_CLIENT_ID, REDDIT_CLIENT_ID, DISCORD_CLIENT_ID
from policyengine import views as policyviews

urlpatterns = [
    path('login/', views.LoginView.as_view(
        template_name='policyadmin/login.html',
        extra_context={
            'server_url': urllib.parse.quote(SERVER_URL, safe=''),
            'slack_client_id': SLACK_CLIENT_ID,
            'reddit_client_id': REDDIT_CLIENT_ID,
            'discord_client_id': DISCORD_CLIENT_ID
        }
    )),
    path('logout/', policyviews.logout),
    path('main/', policyviews.v2),
    path('main/editor/', policyviews.editor),
    path('main/selectrole/', policyviews.selectrole),
    path('main/roleusers/', policyviews.roleusers),
    path('main/roleeditor/', policyviews.roleeditor),
    path('main/selectpolicy/', policyviews.selectpolicy),
    path('main/documenteditor/', policyviews.documenteditor),
    path('main/selectdocument/', policyviews.selectdocument),
    path('main/actions/', policyviews.actions),
    path('main/policyengine/', include('policyengine.urls')),
    path('main/documentation', policyviews.documentation),
    path('jet/', include('jet.urls', 'jet')),  # Django JET URLS
    path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),  # Django JET dashboard URLS
    path('admin/', admin.site.urls),
    path('slack/', include('integrations.slack.urls')),
    path('reddit/', include('integrations.reddit.urls')),
    path('discord/', include('integrations.discord.urls')),
    path('discourse/', include('integrations.discourse.urls')),
    path('outcome/<int:id>', policyviews.post_outcome),
    url(r'^$', policyviews.homepage),
    url('^activity/', include('actstream.urls'))
]
