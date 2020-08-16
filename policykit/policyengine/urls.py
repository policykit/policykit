from django.urls import path
from policyengine import views


urlpatterns = [
    path('initialize_starterkit', views.initialize_starterkit),
    path('error_check', views.error_check),
    path('save_policy', views.policy_action_save)
]
