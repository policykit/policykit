from django.urls import path

from integrations.discourse import views


urlpatterns = [
    path('action', views.action),
    path('configure', views.configure),
    path('request_key', views.request_key),
    path('auth', views.auth)
]
