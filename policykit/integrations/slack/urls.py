from django.urls import path

from integrations.slack import views


urlpatterns = [
    path('oauth', views.oauth),
    path('action', views.action)
]
