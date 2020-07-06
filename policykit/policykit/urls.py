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
from policykit import configure
from policykit.settings import SERVER_URL, REDDIT_CLIENT_ID

urlpatterns = [
    url(r'^login/$', views.login, {
        'template_name': 'policyadmin/login.html',
        'extra_context': {
            'server_url': parse.quote(SERVER_URL),
            'reddit_client_id': REDDIT_CLIENT_ID
        }
    }, name="login"),
    path('', admin_site.urls),
    path('policyengine/', include('policyengine.urls')),
    path('jet/', include('jet.urls', 'jet')),  # Django JET URLS
    path('jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),  # Django JET dashboard URLS
    path('admin/', admin.site.urls),
    path('slack/', include('slackintegration.urls')),
    path('reddit/', include('redditintegration.urls')),
    path('configure/', configure.configure)
]
