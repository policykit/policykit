from django.urls import path

from slackintegration import views


urlpatterns = [
    path('oauth', views.oauth),
    path('action', views.action)
]
