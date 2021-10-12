from django.urls import path

from integrations.discord import views


urlpatterns = [
    path('login', views.discord_login),
    path('install', views.discord_install)
]
