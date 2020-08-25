from django.urls import path
from policyengine import views


urlpatterns = [
    path('initialize_starterkit', views.initialize_starterkit),
    path('error_check', views.error_check),
    path('policy_action_save', views.policy_action_save),
    path('policy_action_remove', views.policy_action_remove),
    path('role_action_save', views.role_action_save),
    path('role_action_users', views.role_action_users)
]
