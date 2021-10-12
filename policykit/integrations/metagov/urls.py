from django.urls import path

from integrations.metagov import views


urlpatterns = [
    path("internal/outcome/<int:id>", views.internal_receive_outcome),
    path("internal/action", views.internal_receive_action),
    # generic integration management views for plugins that don't have policykit apps
    path("enable_integration", views.enable_integration),
    path("disable_integration", views.disable_integration),
]
