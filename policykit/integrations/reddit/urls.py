from django.urls import path

from integrations.reddit import views


urlpatterns = [
    path('oauth', views.oauth),
    path('action', views.action),
    path('init_community_reddit', views.init_community_reddit)
]
