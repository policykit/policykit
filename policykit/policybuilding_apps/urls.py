from django.urls import path
from . import views as cvviews


urlpatterns = [
    # Paths for "CollectiveVoice" policy buildng app
    path('home', cvviews.collectivevoice_home),
    path('edit_expenses', cvviews.collectivevoice_edit_expenses),
    path('create_custom_action', cvviews.create_custom_action),
    path('edit_voting', cvviews.collectivevoice_edit_voting),
    path('create_procedure', cvviews.create_procedure),
    path('edit_followup', cvviews.collectivevoice_edit_followup),
    path('create_execution', cvviews.create_execution),
    path('policy_overview', cvviews.policy_overview),
    path('create_overview', cvviews.create_overview),
    path('success', cvviews.collectivevoice_success),
]
