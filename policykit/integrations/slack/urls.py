from django.urls import path

from integrations.slack import views


urlpatterns = [
    path('login', views.slack_login),
    path('install', views.slack_install),
    path('action', views.action)
]
