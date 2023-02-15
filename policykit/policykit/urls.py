import urllib.parse

from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth import views
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from policyengine import views as policyviews
from policyengine.metagov_app import metagov_handler

# from schema_graph.views import Schema


def plugin_auth_callback(request, plugin_name):
    return metagov_handler.handle_oauth_callback(request, plugin_name)

@csrf_exempt
def handle_incoming_webhook(request, plugin_name, community_slug=None, community_platform_id=None):
    return metagov_handler.handle_incoming_webhook(
        request, plugin_name, community_slug=community_slug, community_platform_id=community_platform_id
    )


urlpatterns = [
    path('login/', views.LoginView.as_view(
        template_name='policyadmin/login.html',
        extra_context={
            'server_url': urllib.parse.quote(settings.SERVER_URL, safe=''),
            'reddit_client_id': settings.REDDIT_CLIENT_ID,
        }
    )),
    path('authorize_platform/', policyviews.authorize_platform),
    path('authenticate_user/', policyviews.authenticate_user),
    path('auth/<str:plugin_name>/callback', plugin_auth_callback),
    path('logout/', policyviews.logout, name="logout"),
    path('main/', policyviews.dashboard),
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
    
    path('embed/populate_templates', policyviews.embed_populate_templates),
    path('embed/select_template', policyviews.embed_select_template),
    path('embed/', policyviews.embed_initial),
    path('embed/setup', policyviews.embed_setup),
    path('embed/summary', policyviews.embed_summary),
    path('embed/update', policyviews.embed_update),
    path('embed/edit', policyviews.embed_edit),
    path('embed/success', policyviews.embed_success),
    path('admin/', admin.site.urls),

    # custom enable/disable views for integrations that use OAuth
    path('slack/', include('integrations.slack.urls')),
    path('reddit/', include('integrations.reddit.urls')),
    path('discord/', include('integrations.discord.urls')),
    path('discourse/', include('integrations.discourse.urls')),
    path('github/', include('integrations.github.urls')),
    path('opencollective/', include('integrations.opencollective.urls')),

    # default enable/disable views
    path('<slug:integration>/enable_integration', policyviews.enable_integration),
    path('<slug:integration>/disable_integration', policyviews.disable_integration),

    url(r'^$', policyviews.homepage),
    url('^activity/', include('actstream.urls')),
    # webhook receivers
    path('api/hooks/<slug:plugin_name>', handle_incoming_webhook),
    path('api/hooks/<slug:plugin_name>/<slug:community_slug>', handle_incoming_webhook),
    path('api/hooks/<slug:plugin_name>/<slug:community_slug>/<slug:community_platform_id>', handle_incoming_webhook),
    # path("schema/", Schema.as_view()),
]
