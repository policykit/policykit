from django.urls import path

from integrations.discourse import views


urlpatterns = [
    path('oauth', views.oauth),
    path('action', views.action),
    path('init_community_discourse', views.init_community_discourse)
]
