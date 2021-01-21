from django.urls import path

from integrations.discourse import views


urlpatterns = [
    path('action', views.action),
    path('configure', views.configure),
    path('auth', views.auth),
    path('user_login', views.user_login),
    path('init_community', views.init_community)
]
