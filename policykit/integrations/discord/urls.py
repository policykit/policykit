from django.urls import path
from integrations.discord import views

urlpatterns = [
    path('oauth', views.oauth)
]
