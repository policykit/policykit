from django.urls import path

from integrations.github import views


urlpatterns = [
    path('install', views.github_install),
]
