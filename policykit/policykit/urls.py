"""policykit URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views
from django.urls import path
from django.conf.urls import include, url
from django.views.generic import TemplateView
import urllib.parse
from policyengine.admin import admin_site
from policykit.settings import SERVER_URL, REDDIT_CLIENT_ID, DISCORD_CLIENT_ID, VERSION
from policyengine import views as policyviews

urlpatterns = [
    path('login/', views.LoginView.as_view(
        template_name='policyadmin/login.html',
        extra_context={
            'server_url': urllib.parse.quote(SERVER_URL, safe=''),
            'reddit_client_id': REDDIT_CLIENT_ID,
            'discord_client_id': DISCORD_CLIENT_ID
        }
    )),
    path('logout/', policyviews.logout),
    path('main/', policyviews.v2 if VERSION == "v2" else admin_site.urls),
    path('main/policyengine/', include('policyengine.urls')),
    path('jet/', include('jet.urls', 'jet')),  # Django JET URLS
    path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),  # Django JET dashboard URLS
    path('admin/', admin.site.urls),
    path('slack/', include('slackintegration.urls')),
    path('reddit/', include('redditintegration.urls')),
    path('discord/', include('discordintegration.urls')),
    url(r'^$', policyviews.homepage),
]
