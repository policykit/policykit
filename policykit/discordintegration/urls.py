from django.urls import path

from discordintegration import views


urlpatterns = [
    path('oauth', views.oauth),
    path('action', views.action)
]
