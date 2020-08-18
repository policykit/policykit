from django.urls import path
from policyengine import views
from .feeds import LatestPostsFeed


urlpatterns = [
    path('initialize_starterkit', views.initialize_starterkit),
    path('error_check', views.error_check),
    path('policy_action_save', views.policy_action_save),
    path('feed/rss', LatestPostsFeed(), name='post_feed')
]
