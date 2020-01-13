from django.urls import path
from govrules import views


urlpatterns = [
    path('submit_proposal', views.submit_proposal)
]