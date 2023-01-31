from django.urls import path

from integrations.opencollective import views


urlpatterns = [
    path('install', views.opencollective_install),
]
