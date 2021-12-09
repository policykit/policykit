from django.urls import path

from integrations.discord import views


urlpatterns = [
    path('login', views.discord_login),
    path('login_selected_guild', views.login_selected_guild),
    path('install', views.discord_install)
]
