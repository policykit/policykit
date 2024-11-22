from django.urls import path

from integrations.opencollective import views


urlpatterns = [
    path('install', views.opencollective_install),
    path('disable_integration_without_deletion', views.disable_integration_without_deletion),
]
