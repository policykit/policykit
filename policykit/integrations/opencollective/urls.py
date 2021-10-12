from django.urls import path

from integrations.opencollective import views


urlpatterns = [
    path('enable_integration', views.enable_integration),
    path('disable_integration', views.disable_integration)
]
